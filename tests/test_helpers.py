import pytest

from aiotnse.exceptions import RegionNotFound, InvalidAccountNumber
from aiotnse.helpers import get_region
from tests.common import ACCOUNT


class TestTNSEApi:
    def test_get_region(self):
        account = ACCOUNT
        region = get_region(account)
        assert region == "rostov"

        with pytest.raises(RegionNotFound) as exc:
            region = get_region("000000000000")

        with pytest.raises(InvalidAccountNumber) as exc:
            region = get_region("000000000")
