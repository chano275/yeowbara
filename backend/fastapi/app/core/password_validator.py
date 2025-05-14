import re
from typing import Dict, Union, Tuple

def validate_password(password: str) -> Tuple[bool, str]:
    """
    비밀번호 유효성을 검증합니다.
    
    규칙:
    1. 최소 8자 이상
    2. 영어 포함
    3. 숫자 포함
    4. 특수문자 포함
    
    Returns:
        Tuple[bool, str]: (유효성 여부, 오류 메시지)
    """
    # 최소 길이 검증
    if len(password) < 8:
        return False, "비밀번호는 8자 이상이어야 합니다."
    
    # 영어 포함 검증
    if not re.search(r'[a-zA-Z]', password):
        return False, "비밀번호는 적어도 하나의 영문자를 포함해야 합니다."
    
    # 숫자 포함 검증
    if not re.search(r'\d', password):
        return False, "비밀번호는 적어도 하나의 숫자를 포함해야 합니다."
    
    # 특수문자 포함 검증
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "비밀번호는 적어도 하나의 특수문자(!@#$%^&*(),.?\":{}|<>)를 포함해야 합니다."
    
    return True, "유효한 비밀번호입니다."
