from typing import Any, Dict

from knowledge_base.embedchain.helpers.json_serializable import JSONSerializable


class BaseConfig(JSONSerializable):
    """
    Base config.
    """

    def __init__(self):
        """Initializes a configuration class for a class."""
        pass

    def as_dict(self) -> Dict[str, Any]:
        """Return config object as a dict

        :return: config object as dict
        :rtype: Dict[str, Any]
        """
        return vars(self)
