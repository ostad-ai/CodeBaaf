# 10 - Exception Handling
# Preventing the program from crashing on errors.

print("Let's try to divide two numbers.")

try:
    num1 = int(input("Enter a number: "))
    num2 = int(input("Enter another number: "))
    result = num1 / num2
    print(f"Result: {result}")

except ValueError:
    print("Error: Please enter valid numbers.")
except ZeroDivisionError:
    print("Error: You cannot divide by zero!")
finally:
    print("Execution finished.")