# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright 2022 Canonical Ltd.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Functions to serialize/deserialize credentials for Candid and Ubuntu One SSO."""

import json
from typing import Any, Dict, Literal

import pydantic
from pydantic import BaseModel, Field

from . import errors


class CandidModel(BaseModel):
    """Model for Candid credentials."""

    token_type: Literal["macaroon"] = Field("macaroon", alias="t")
    value: str = Field(..., alias="v")

    def marshal(self) -> Dict[str, Any]:
        """Create a dictionary containing the Candid credentials."""
        return self.dict(by_alias=True)

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]) -> "CandidModel":
        """Create Candid model from dictionary data."""
        return cls(**data)


def marshal_candid_credentials(candid_creds: str) -> str:
    """Serialize Candid credentials for storage.

    This function creates a string that contains the desired `candid_creds` but also
    stores their "type", for unmarshalling later with `unmarshal_candid_credentials()`.

    :param candid_creds: The actual Candid credentials.
    :return: A payload string ready to be passed to Auth.set_credentials()
    """
    return json.dumps(CandidModel(v=candid_creds).marshal())  # pyright: ignore


def unmarshal_candid_credentials(marshalled_creds: str) -> str:
    """Deserialize previously stored Candid credentials.

    This function is meant to be called with the returned value from
    Auth.get_credentials(). As such, it supports parsing credentials from before we
    stored the `token_type`. Overall, this means supporting the scenarios where
    `marshalled_creds` is:

    (1) a regular JSON string generated by `marshal_candid_credentials()`;
    (2) a regular JSON string that was *not* generated by `marshal_candid_credentials()`
        but contains the Candid macaroon as a serialized dict;
    (3) a string that is not JSON but contains the serialized (non-dict) Candid macaroon.

    In addition, the function will raise a CredentialsNotParseable error when
    `marshalled_creds` is:

    (4) A regular JSON string containing a dict that *has* a type, but is *not* Candid.

    :param marshalled_creds: The credentials retrieved from auth storage.
    :return: The actual Candid credentials.
    """
    data: Dict[str, Any] = {}
    try:
        creds = json.loads(marshalled_creds)
    except json.JSONDecodeError:
        # Case (3): "opaque" serialized macaroon.
        data["v"] = marshalled_creds
    else:
        if "t" in creds:
            # Cases (1) and (4): dict containing the credentials type.
            data = creds
        else:
            # Case (2): dict without the type.
            data["v"] = marshalled_creds

    try:
        return CandidModel.unmarshal(data).value
    except pydantic.ValidationError as err:
        # Case (4): dict for some other credential type.
        raise errors.CredentialsNotParseable(
            "Expected valid Candid credentials"
        ) from err


class UbuntuOneMacaroons(BaseModel):
    """Model representation of the set of macaroons used in Ubuntu SSO."""

    root: str = Field(..., alias="r")
    discharge: str = Field(..., alias="d")

    def with_discharge(self, discharge: str) -> "UbuntuOneMacaroons":
        """Create a copy of this UbuntuOneMacaroons with a different discharge macaroon."""
        return self.copy(update={"d": discharge})


class UbuntuOneModel(BaseModel):
    """Model for Ubuntu One credentials."""

    token_type: Literal["u1-macaroon"] = Field("u1-macaroon", alias="t")
    value: UbuntuOneMacaroons = Field(..., alias="v")

    def marshal(self) -> Dict[str, Any]:
        """Create a dictionary containing the Ubuntu One credentials."""
        return self.dict(by_alias=True)

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]) -> "UbuntuOneModel":
        """Create Candid model from dictionary data."""
        return cls(**data)


def marshal_u1_credentials(u1_creds: UbuntuOneMacaroons) -> str:
    """Serialize Ubuntu One credentials for storage.

    This function creates a string that contains the desired `u1_creds` but also
    stores their "type", for unmarshalling later with `unmarshal_u1_credentials()`.

    :param u1_creds: The actual Ubuntu One macaroons credentials.
    :return: A payload string ready to be passed to Auth.set_credentials()
    """
    return json.dumps(UbuntuOneModel(v=u1_creds).marshal())  # pyright: ignore


def unmarshal_u1_credentials(marshalled_creds: str) -> UbuntuOneMacaroons:
    """Deserialize previously stored Ubuntu One credentials.

    This function is meant to be called with the returned value from
    Auth.get_credentials(). As such, it supports parsing credentials from before we
    stored the `token_type`. Overall, this means supporting the scenarios where
    `marshalled_creds` is:

    (1) a regular JSON string generated by `marshal_u1_credentials()`;
    (2) a regular JSON string that was *not* generated by `marshal_u1_credentials()`
        but contains the `UbuntuOneMacaroons` values as a serialized dict;

    In addition, the function will raise a CredentialsNotParseable error when
    `marshalled_creds` is:

    (3) a string that is not JSON.
    (4) A regular JSON string containing a dict that *has* a type, but is *not* Ubuntu One.

    :param marshalled_creds: The credentials retrieved from auth storage.
    :return: The actual Ubuntu One credentials.
    """
    data: Dict[str, Any] = {}

    try:
        creds = json.loads(marshalled_creds)
    except json.JSONDecodeError as err:
        # Case (3).
        raise errors.CredentialsNotParseable(
            "Expected valid Ubuntu One credentials"
        ) from err
    else:
        if "t" in creds:
            # Cases (1) and (4).
            data = creds
        else:
            # Case (2).
            data["v"] = creds

    try:
        return UbuntuOneModel.unmarshal(data).value
    except pydantic.ValidationError as err:
        # Case (4): dict for some other credential type.
        raise errors.CredentialsNotParseable(
            "Expected valid Ubuntu One credentials"
        ) from err
