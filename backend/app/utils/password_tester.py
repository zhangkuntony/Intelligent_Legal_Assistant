"""
密码测试工具
用于生成和验证测试密码
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.app.core.security import get_password_hash, verify_password


def generate_test_passwords() -> dict:
    """
    生成测试密码哈希
    
    Returns:
        dict: 包含测试密码和对应哈希值的字典
    """
    test_passwords = {
        "admin": "123456",
        "user": "user123",
        "testuser": "123456",
        "demo": "demo123",
        "strong_password": "StrongP@ssw0rd123!"
    }
    
    result = {}
    for username, password in test_passwords.items():
        hashed_password = get_password_hash(password)
        result[username] = {
            "password": password,
            "hashed_password": hashed_password,
            "verified": verify_password(password, hashed_password)
        }
    
    return result


def verify_test_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证测试密码
    
    Args:
        plain_password: 明文密码
        hashed_password: 哈希密码
        
    Returns:
        bool: 验证结果
    """
    return verify_password(plain_password, hashed_password)


def print_test_passwords():
    """打印测试密码信息"""
    passwords = generate_test_passwords()
    
    print("=" * 60)
    print("测试密码哈希生成器")
    print("=" * 60)
    
    for username, data in passwords.items():
        print(f"\n用户名: {username}")
        print(f"密码: {data['password']}")
        print(f"哈希值: {data['hashed_password']}")
        print(f"验证结果: {'✓ 验证成功' if data['verified'] else '✗ 验证失败'}")
        print("-" * 40)


def get_password_hash_for_insert(password: str) -> str:
    """
    生成用于数据库插入的密码哈希
    
    Args:
        password: 明文密码
        
    Returns:
        str: 哈希密码
    """
    return get_password_hash(password)


if __name__ == "__main__":
    # 直接运行此文件时打印测试密码
    print_test_passwords()
    
    # 示例：生成特定密码的哈希
    print("\n" + "=" * 60)
    print("示例：生成单个密码哈希")
    print("=" * 60)
    
    example_password = "example123"
    hashed = get_password_hash_for_insert(example_password)
    print(f"密码: {example_password}")
    print(f"哈希值: {hashed}")
    print(f"验证结果: {verify_test_password(example_password, hashed)}")