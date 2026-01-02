from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 生成正确的密码哈希
password = "123456"
correct_hash = pwd_context.hash(password)

print("=" * 50)
print("密码修复工具")
print("=" * 50)
print(f"密码: {password}")
print(f"正确的bcrypt哈希: {correct_hash}")
print(f"哈希长度: {len(correct_hash)}")

# 验证哈希
try:
    identified = pwd_context.identify(correct_hash)
    verified = pwd_context.verify(password, correct_hash)
    print(f"哈希可识别: {identified}")
    print(f"哈希验证通过: {verified}")
except Exception as e:
    print(f"错误: {e}")

print("\nSQL更新语句:")
print(f"UPDATE users SET password_hash = '{correct_hash}' WHERE username = 'admin';")
print("\n直接执行的命令:")
print(f"docker exec legal_assistant_db psql -U legal_assistant -d legal_assistant -c \"UPDATE users SET password_hash = '{correct_hash}' WHERE username = 'admin';\"")