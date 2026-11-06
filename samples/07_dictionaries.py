# 07 - Dictionaries
# Storing data in key-value pairs.

user = {
    "name": "Aria",
    "role": "AI Engineer",
    "status": "Active"
}

print(f"User Name: {user['name']}")
print(f"Role: {user['role']}")

# Adding a new key-value pair
user["loves_coding"] = True
print("Updated User Data:", user)