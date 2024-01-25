# If you want to use OCI SDK from the Python code itself (and not from the ~/.oci/config file, use this script.)

config = {
    "user": "<your_user_ocid>",
    "key_file": "<full_path_to_your_private_key>",
    "fingerprint": "<fingerprint_of_your_public_key>",
    "tenancy": "<your_tenancy_ocid>",
    "region": "<your_oci_region>"
}

from oci.config import validate_config
validate_config(config)