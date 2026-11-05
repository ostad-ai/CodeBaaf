# Test Python's built-in Turtle graphics.
import turtle

# Set up the screen
screen = turtle.Screen()
screen.title("CodeBaaf Turtle Test")
screen.bgcolor("black")

# Set up the turtle
t = turtle.Turtle()
t.color("cyan")
t.pensize(3)
t.speed(0)

# Draw a beautiful star pattern
for i in range(36):
    t.forward(100)
    t.right(170)

# Keep the window open
turtle.done()