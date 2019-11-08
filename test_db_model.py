import uuid

import pytest
from marshmallow import ValidationError

from app import db
from app.models import Host
from app.models import HostSchema
from app.utils import Tag

"""
These tests are for testing the db model classes outside of the api.
"""


def _create_host(insights_id=None, fqdn=None, display_name=None, tags=None):
    if not insights_id:
        insights_id = str(uuid.uuid4())
    canonical_facts = {"insights_id": insights_id}
    if fqdn is not None:
        canonical_facts["fqdn"] = fqdn
    host = Host(canonical_facts, display_name=display_name, account="00102", tags=tags)
    db.session.add(host)
    db.session.commit()
    return host


def test_create_host_with_fqdn_and_display_name_as_empty_str(flask_app_fixture):
    # Verify that the display_name is populated from the fqdn
    fqdn = "spacely_space_sprockets.orbitcity.com"
    created_host = _create_host(fqdn=fqdn, display_name="")
    assert created_host.display_name == fqdn


def test_create_host_with_display_name_and_fqdn_as_empty_str(flask_app_fixture):
    # Verify that the display_name is populated from the id
    created_host = _create_host(fqdn="", display_name="")
    assert created_host.display_name == str(created_host.id)


def test_update_existing_host_fix_display_name_using_existing_fqdn(flask_app_fixture):
    expected_fqdn = "host1.domain1.com"
    insights_id = str(uuid.uuid4())
    existing_host = _create_host(insights_id=insights_id, fqdn=expected_fqdn, display_name=None)

    # Clear the display_name
    existing_host.display_name = None
    db.session.commit()
    assert existing_host.display_name is None

    # Update the host
    input_host = Host({"insights_id": insights_id}, display_name="")
    existing_host.update(input_host)

    assert existing_host.display_name == expected_fqdn


def test_update_existing_host_fix_display_name_using_input_fqdn(flask_app_fixture):
    # Create an "existing" host
    fqdn = "host1.domain1.com"
    existing_host = _create_host(fqdn=fqdn, display_name=None)

    # Clear the display_name
    existing_host.display_name = None
    db.session.commit()
    assert existing_host.display_name is None

    # Update the host
    expected_fqdn = "different.domain1.com"
    input_host = Host({"fqdn": expected_fqdn}, display_name="")
    existing_host.update(input_host)

    assert existing_host.display_name == expected_fqdn


def test_update_existing_host_fix_display_name_using_id(flask_app_fixture):
    # Create an "existing" host
    existing_host = _create_host(fqdn=None, display_name=None)

    # Clear the display_name
    existing_host.display_name = None
    db.session.commit()
    assert existing_host.display_name is None

    # Update the host
    input_host = Host({"insights_id": existing_host.canonical_facts["insights_id"]}, display_name="")
    existing_host.update(input_host)

    assert existing_host.display_name == existing_host.id


def test_create_host_without_system_profile(flask_app_fixture):
    # Test the situation where the db/sqlalchemy sets the
    # system_profile_facts to None
    created_host = _create_host(fqdn="fred.flintstone.com", display_name="fred")
    assert created_host.system_profile_facts == {}


def test_create_host_with_system_profile(flask_app_fixture):
    system_profile_facts = {"number_of_cpus": 1}
    host = Host(
        {"fqdn": "fred.flintstone.com"},
        display_name="display_name",
        account="00102",
        system_profile_facts=system_profile_facts,
    )
    db.session.add(host)
    db.session.commit()

    assert host.system_profile_facts == system_profile_facts


@pytest.mark.parametrize(
    "tags",
    [
        [{"namespace": "Sat", "key": "env", "value": "prod"}, {"namespace": "AWS", "key": "env", "value": "ci"}],
        [{"namespace": "Sat", "key": "env"}, {"namespace": "AWS", "key": "env"}],
    ],
)
def test_host_schema_valid_tags(tags):
    host = {"fqdn": "fred.flintstone.com", "display_name": "display_name", "account": "00102", "tags": tags}
    validated_host = HostSchema(strict=True).load(host)

    assert validated_host.data["tags"] == tags


# TODO
# look into making this acutally work. Will have to add real validation
@pytest.mark.parametrize("tags", [[{"namespace": "Sat/"}], [{"value": "bad_tag"}]])
def test_host_schema_invalid_tags(tags):
    host = {"fqdn": "fred.flintstone.com", "display_name": "display_name", "account": "00102", "tags": tags}
    with pytest.raises(ValidationError) as excinfo:
        _ = HostSchema(strict=True).load(host)

    assert "Key is requred in all tags" in str(excinfo.value)


def test_tag_deserialization():
    tags = [
        {"namespace": "Sat", "key": "env", "value": "prod"},
        {"namespace": "Sat", "key": "env", "value": "test"},
        {"namespace": "Sat", "key": "geo", "value": "somewhere"},
        {"namespace": "AWS", "key": "env", "value": "ci"},
        {"namespace": "AWS", "key": "env"},
    ]
    expected_tags = {"Sat": {"env": ["prod", "test"], "geo": ["somewhere"]}, "AWS": {"env": ["ci"]}}
    deserialized_tags = Tag.create_nested_from_tags(Tag.create_structered_tags_from_tag_data_list(tags))

    assert sorted(deserialized_tags["Sat"]["env"]) == sorted(expected_tags["Sat"]["env"])
    assert sorted(deserialized_tags["Sat"]["geo"]) == sorted(expected_tags["Sat"]["geo"])
    assert sorted(deserialized_tags["AWS"]["env"]) == sorted(expected_tags["AWS"]["env"])


@pytest.mark.parametrize(
    "tags",
    [
        [{"namespace": "Sat", "key": "env", "value": "prod"}, {"namespace": "AWS", "key": "env", "value": "ci"}],
        [{"namespace": "Sat", "key": "env"}, {"namespace": "AWS", "key": "env"}],
    ],
)
def test_create_host_with_tags(flask_app_fixture, tags):
    host = _create_host(fqdn="fred.flintstone.com", display_name="display_name", tags=tags)

    assert host.tags == tags


def test_update_host_with_tags(flask_app_fixture):
    insights_id = str(uuid.uuid4())
    old_tags = Tag("Sat", "env", "prod").to_nested()
    existing_host = _create_host(insights_id=insights_id, display_name="tagged", tags=old_tags)

    assert existing_host.tags == old_tags

    # On update each namespace in the input host's tags should be updated.
    new_tags = Tag.create_nested_from_tags([Tag("Sat", "env", "ci"), Tag("AWS", "env", "prod")])
    input_host = _create_host(insights_id=insights_id, display_name="tagged", tags=new_tags)
    existing_host.update(input_host)

    assert existing_host.tags == new_tags


def test_update_host_with_no_tags(flask_app_fixture):
    insights_id = str(uuid.uuid4())
    old_tags = Tag("Sat", "env", "prod").to_nested()
    existing_host = _create_host(insights_id=insights_id, display_name="tagged", tags=old_tags)

    # Updating a host should not remove any existing tags if tags are missing from the input host
    input_host = _create_host(insights_id=insights_id, display_name="tagged")
    existing_host.update(input_host)

    assert existing_host.tags == old_tags
