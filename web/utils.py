# web/utils.py

import hashlib
import hmac

def verify_webapp_data(token: str, data_check_string: str, hash: str) -> bool:
    secret_key = hashlib.sha256(token.encode()).digest()
    data_check_list = data_check_string.split("&")
    data_check_list.sort()
    data_check_sorted = "\n".join(data_check_list)
    computed_hash = hmac.new(secret_key, data_check_sorted.encode(), hashlib.sha256).hexdigest()
    return computed_hash == hash
