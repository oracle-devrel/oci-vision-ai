# Please check https://docs.oracle.com/en-us/iaas/Content/API/Concepts/apisigningkey.htm
# for help on how to generate a key-pair and calculate the key fingerprint.

from oci.config import from_file, validate_config

config = from_file(profile_name='DEFAULT')

validate_config(config)


# https://docs.oracle.com/en-us/iaas/tools/python/2.116.0/configuration.html