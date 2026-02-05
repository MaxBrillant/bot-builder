"""
Example Flow Definitions
Provides pre-built example flows for new user onboarding
"""

def get_customer_support_menu_flow():
    """
    Example Flow 1: Customer Support Menu

    Demonstrates:
    - MESSAGE nodes for information display
    - MENU nodes with static options
    - Basic routing and navigation

    Trigger: MENU
    """
    return {
        "name": "Customer Support Menu",
        "trigger_keywords": ["MENU"],
        "start_node_id": "welcome",
        "nodes": {
            "welcome": {
                "id": "welcome",
                "name": "Welcome Message",
                "type": "MESSAGE",
                "config": {
                    "type": "MESSAGE",
                    "text": "Hello! Welcome to our support center. I'm here to help you today."
                },
                "routes": [
                    {"condition": "true", "target_node": "main_menu"}
                ],
                "position": {"x": 100, "y": 200}
            },
            "main_menu": {
                "id": "main_menu",
                "name": "Main Menu",
                "type": "MENU",
                "config": {
                    "type": "MENU",
                    "text": "Which department would you like to reach?",
                    "source_type": "STATIC",
                    "static_options": [
                        {"label": "Technical Support"},
                        {"label": "Billing and Payments"},
                        {"label": "General Questions"}
                    ],
                    "error_message": "Invalid selection. Please enter 1 for Technical Support, 2 for Billing, or 3 for General Questions."
                },
                "routes": [
                    {"condition": "selection == 1", "target_node": "technical_response"},
                    {"condition": "selection == 2", "target_node": "billing_response"},
                    {"condition": "selection == 3", "target_node": "general_response"},
                    {"condition": "true", "target_node": "end"}
                ],
                "position": {"x": 440, "y": 200}
            },
            "technical_response": {
                "id": "technical_response",
                "name": "Technical Response",
                "type": "MESSAGE",
                "config": {
                    "type": "MESSAGE",
                    "text": "You've reached Technical Support. Please describe the issue you're experiencing and I'll do my best to help you resolve it."
                },
                "routes": [
                    {"condition": "true", "target_node": "end"}
                ],
                "position": {"x": 960, "y": 40}
            },
            "billing_response": {
                "id": "billing_response",
                "name": "Billing Response",
                "type": "MESSAGE",
                "config": {
                    "type": "MESSAGE",
                    "text": "You've reached Billing and Payments. Please provide your account details and I'll help you with your billing inquiry."
                },
                "routes": [
                    {"condition": "true", "target_node": "end"}
                ],
                "position": {"x": 960, "y": 200}
            },
            "general_response": {
                "id": "general_response",
                "name": "General Response",
                "type": "MESSAGE",
                "config": {
                    "type": "MESSAGE",
                    "text": "I'm here to help with any questions you might have. What can I assist you with today?"
                },
                "routes": [
                    {"condition": "true", "target_node": "end"}
                ],
                "position": {"x": 960, "y": 360}
            },
            "end": {
                "id": "end",
                "name": "End",
                "type": "END",
                "config": {
                    "type": "END"
                },
                "position": {"x": 1300, "y": 200}
            }
        }
    }


def get_onboarding_form_flow():
    """
    Example Flow 2: User Onboarding Form

    Demonstrates:
    - PROMPT nodes for data collection
    - Input validation with regex
    - MENU with dynamic options and output_mapping
    - Template variables ({{variable}})
    - Flow variables with types

    Trigger: ONBOARDING
    """
    return {
        "name": "User Onboarding Form",
        "trigger_keywords": ["ONBOARDING"],
        "variables": {
            "user_name": {"type": "STRING", "default": ""},
            "user_email": {"type": "STRING", "default": ""},
            "user_role": {"type": "STRING", "default": ""},
            "available_roles": {"type": "ARRAY", "default": [
                {"name": "Developer"},
                {"name": "Designer"},
                {"name": "Manager"},
                {"name": "Other"}
            ]}
        },
        "start_node_id": "welcome",
        "nodes": {
            "welcome": {
                "id": "welcome",
                "name": "Welcome",
                "type": "MESSAGE",
                "config": {
                    "type": "MESSAGE",
                    "text": "Welcome! I'll help you get set up with your account. This will only take a minute."
                },
                "routes": [
                    {"condition": "true", "target_node": "ask_name"}
                ],
                "position": {"x": 100, "y": 200}
            },
            "ask_name": {
                "id": "ask_name",
                "name": "Ask Name",
                "type": "PROMPT",
                "config": {
                    "type": "PROMPT",
                    "text": "What's your full name?",
                    "save_to_variable": "user_name"
                },
                "routes": [
                    {"condition": "true", "target_node": "ask_email"}
                ],
                "position": {"x": 440, "y": 200}
            },
            "ask_email": {
                "id": "ask_email",
                "name": "Ask Email",
                "type": "PROMPT",
                "config": {
                    "type": "PROMPT",
                    "text": "What's your email address?",
                    "save_to_variable": "user_email",
                    "validation": {
                        "type": "REGEX",
                        "rule": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
                        "error_message": "Please enter a valid email address (e.g., name@example.com)"
                    }
                },
                "routes": [
                    {"condition": "true", "target_node": "ask_role"}
                ],
                "position": {"x": 780, "y": 200}
            },
            "ask_role": {
                "id": "ask_role",
                "name": "Ask Role",
                "type": "MENU",
                "config": {
                    "type": "MENU",
                    "text": "What's your role?",
                    "source_type": "DYNAMIC",
                    "source_variable": "available_roles",
                    "item_template": "{{item.name}}",
                    "output_mapping": [
                        {"source_path": "name", "target_variable": "user_role"}
                    ],
                    "error_message": "Invalid selection. Please enter a number from the list of available roles."
                },
                "routes": [
                    {"condition": "true", "target_node": "confirmation"}
                ],
                "position": {"x": 1120, "y": 200}
            },
            "confirmation": {
                "id": "confirmation",
                "name": "Confirmation",
                "type": "MESSAGE",
                "config": {
                    "type": "MESSAGE",
                    "text": "Thank you! Your account has been set up with the following information:\n\nName: {{user_name}}\nEmail: {{user_email}}\nRole: {{user_role}}\n\nYou're all ready to go."
                },
                "routes": [
                    {"condition": "true", "target_node": "end"}
                ],
                "position": {"x": 1460, "y": 200}
            },
            "end": {
                "id": "end",
                "name": "End",
                "type": "END",
                "config": {
                    "type": "END"
                },
                "position": {"x": 1800, "y": 200}
            }
        }
    }


def get_weather_lookup_flow():
    """
    Example Flow 3: Weather Lookup Bot

    Demonstrates:
    - MENU with predefined array of cities
    - output_mapping to extract multiple fields (name, latitude, longitude)
    - API_ACTION with dynamic URL parameters using template variables
    - response_map for extracting API data
    - API_ACTION success/error routing

    Trigger: WEATHER
    API: Open-Meteo (free, no auth required)
    """
    return {
        "name": "Weather Lookup Bot",
        "trigger_keywords": ["WEATHER"],
        "variables": {
            "available_cities": {"type": "ARRAY", "default": [
                {"name": "London", "latitude": 51.5074, "longitude": -0.1278},
                {"name": "New York", "latitude": 40.7128, "longitude": -74.0060},
                {"name": "Tokyo", "latitude": 35.6762, "longitude": 139.6503},
                {"name": "Paris", "latitude": 48.8566, "longitude": 2.3522},
                {"name": "Sydney", "latitude": -33.8688, "longitude": 151.2093},
                {"name": "Dubai", "latitude": 25.2048, "longitude": 55.2708},
                {"name": "Singapore", "latitude": 1.3521, "longitude": 103.8198},
                {"name": "Mumbai", "latitude": 19.0760, "longitude": 72.8777}
            ]},
            "city": {"type": "STRING", "default": ""},
            "latitude": {"type": "NUMBER", "default": 0},
            "longitude": {"type": "NUMBER", "default": 0},
            "temperature": {"type": "NUMBER", "default": 0},
            "weather_description": {"type": "STRING", "default": ""}
        },
        "start_node_id": "welcome",
        "nodes": {
            "welcome": {
                "id": "welcome",
                "name": "Welcome",
                "type": "MESSAGE",
                "config": {
                    "type": "MESSAGE",
                    "text": "Hello! I can help you check the current weather. Please select a city from the list below."
                },
                "routes": [
                    {"condition": "true", "target_node": "select_city"}
                ],
                "position": {"x": 100, "y": 200}
            },
            "select_city": {
                "id": "select_city",
                "name": "Select City",
                "type": "MENU",
                "config": {
                    "type": "MENU",
                    "text": "Which city would you like to check?",
                    "source_type": "DYNAMIC",
                    "source_variable": "available_cities",
                    "item_template": "{{item.name}}",
                    "output_mapping": [
                        {"source_path": "name", "target_variable": "city"},
                        {"source_path": "latitude", "target_variable": "latitude"},
                        {"source_path": "longitude", "target_variable": "longitude"}
                    ],
                    "error_message": "Invalid selection. Please enter a number from the list of available cities."
                },
                "routes": [
                    {"condition": "true", "target_node": "fetch_weather"}
                ],
                "position": {"x": 440, "y": 200}
            },
            "fetch_weather": {
                "id": "fetch_weather",
                "name": "Fetch Weather",
                "type": "API_ACTION",
                "config": {
                    "type": "API_ACTION",
                    "request": {
                        "method": "GET",
                        "url": "https://api.open-meteo.com/v1/forecast?latitude={{latitude}}&longitude={{longitude}}&current_weather=true"
                    },
                    "response_map": [
                        {"source_path": "current_weather.temperature", "target_variable": "temperature"},
                        {"source_path": "current_weather.weathercode", "target_variable": "weather_description"}
                    ]
                },
                "routes": [
                    {"condition": "success", "target_node": "display_weather"},
                    {"condition": "error", "target_node": "api_error"}
                ],
                "position": {"x": 780, "y": 200}
            },
            "display_weather": {
                "id": "display_weather",
                "name": "Display Weather",
                "type": "MESSAGE",
                "config": {
                    "type": "MESSAGE",
                    "text": "Here's the current weather in {{city}}:\n\nTemperature: {{temperature}}°C"
                },
                "routes": [
                    {"condition": "true", "target_node": "end"}
                ],
                "position": {"x": 1240, "y": 180}
            },
            "api_error": {
                "id": "api_error",
                "name": "API Error",
                "type": "MESSAGE",
                "config": {
                    "type": "MESSAGE",
                    "text": "I'm sorry, I wasn't able to retrieve the weather information right now. Please try again in a moment."
                },
                "routes": [
                    {"condition": "true", "target_node": "end"}
                ],
                "position": {"x": 1240, "y": 340}
            },
            "end": {
                "id": "end",
                "name": "End",
                "type": "END",
                "config": {
                    "type": "END"
                },
                "position": {"x": 1650, "y": 200}
            }
        }
    }


def get_quiz_flow():
    """
    Example Flow 4: Simple Quiz

    Demonstrates:
    - Multiple PROMPT nodes for questions
    - LOGIC_EXPRESSION for answer checking
    - Conditional routing based on answers
    - Input validation with expressions

    Trigger: QUIZ
    """
    return {
        "name": "Simple Quiz",
        "trigger_keywords": ["QUIZ"],
        "variables": {
            "answer1": {"type": "STRING", "default": ""},
            "answer2": {"type": "STRING", "default": ""},
            "answer3": {"type": "STRING", "default": ""}
        },
        "start_node_id": "welcome",
        "nodes": {
            "welcome": {
                "id": "welcome",
                "name": "Welcome",
                "type": "MESSAGE",
                "config": {
                    "type": "MESSAGE",
                    "text": "Welcome to the quick trivia quiz! I'll ask you 3 questions. Let's see how well you do."
                },
                "routes": [
                    {"condition": "true", "target_node": "question1"}
                ],
                "position": {"x": 100, "y": 100}
            },
            "question1": {
                "id": "question1",
                "name": "Question 1",
                "type": "PROMPT",
                "config": {
                    "type": "PROMPT",
                    "text": "Question 1: What is the capital of France?",
                    "save_to_variable": "answer1"
                },
                "routes": [
                    {"condition": "true", "target_node": "check_answer1"}
                ],
                "position": {"x": 440, "y": 100}
            },
            "check_answer1": {
                "id": "check_answer1",
                "name": "Check Answer 1",
                "type": "LOGIC_EXPRESSION",
                "config": {
                    "type": "LOGIC_EXPRESSION"
                },
                "routes": [
                    {"condition": "context.answer1 == \"Paris\" || context.answer1 == \"paris\"", "target_node": "correct1"},
                    {"condition": "true", "target_node": "question2"}
                ],
                "position": {"x": 780, "y": 100}
            },
            "correct1": {
                "id": "correct1",
                "name": "Correct 1",
                "type": "MESSAGE",
                "config": {
                    "type": "MESSAGE",
                    "text": "Correct! Paris is the capital of France."
                },
                "routes": [
                    {"condition": "true", "target_node": "question2"}
                ],
                "position": {"x": 1300, "y": 160}
            },
            "question2": {
                "id": "question2",
                "name": "Question 2",
                "type": "PROMPT",
                "config": {
                    "type": "PROMPT",
                    "text": "Question 2: How many continents are there? Enter a number.",
                    "save_to_variable": "answer2",
                    "validation": {
                        "type": "EXPRESSION",
                        "rule": "input.isNumeric()",
                        "error_message": "Please enter a number."
                    }
                },
                "routes": [
                    {"condition": "true", "target_node": "check_answer2"}
                ],
                "position": {"x": 100, "y": 400}
            },
            "check_answer2": {
                "id": "check_answer2",
                "name": "Check Answer 2",
                "type": "LOGIC_EXPRESSION",
                "config": {
                    "type": "LOGIC_EXPRESSION"
                },
                "routes": [
                    {"condition": "context.answer2 == \"7\"", "target_node": "correct2"},
                    {"condition": "true", "target_node": "question3"}
                ],
                "position": {"x": 440, "y": 400}
            },
            "correct2": {
                "id": "correct2",
                "name": "Correct 2",
                "type": "MESSAGE",
                "config": {
                    "type": "MESSAGE",
                    "text": "That's right! There are 7 continents."
                },
                "routes": [
                    {"condition": "true", "target_node": "question3"}
                ],
                "position": {"x": 940, "y": 460}
            },
            "question3": {
                "id": "question3",
                "name": "Question 3",
                "type": "PROMPT",
                "config": {
                    "type": "PROMPT",
                    "text": "Question 3: Is the Earth flat? Answer yes or no.",
                    "save_to_variable": "answer3"
                },
                "routes": [
                    {"condition": "true", "target_node": "check_answer3"}
                ],
                "position": {"x": 100, "y": 680}
            },
            "check_answer3": {
                "id": "check_answer3",
                "name": "Check Answer 3",
                "type": "LOGIC_EXPRESSION",
                "config": {
                    "type": "LOGIC_EXPRESSION"
                },
                "routes": [
                    {"condition": "context.answer3 == \"no\" || context.answer3 == \"No\" || context.answer3 == \"NO\"", "target_node": "correct3"},
                    {"condition": "true", "target_node": "results"}
                ],
                "position": {"x": 440, "y": 680}
            },
            "correct3": {
                "id": "correct3",
                "name": "Correct 3",
                "type": "MESSAGE",
                "config": {
                    "type": "MESSAGE",
                    "text": "Correct! The Earth is round, not flat."
                },
                "routes": [
                    {"condition": "true", "target_node": "results"}
                ],
                "position": {"x": 1000, "y": 740}
            },
            "results": {
                "id": "results",
                "name": "Results",
                "type": "MESSAGE",
                "config": {
                    "type": "MESSAGE",
                    "text": "Quiz complete! Thank you for playing.\n\nYour Answers:\n1. Capital of France: {{answer1}} (Correct: Paris)\n2. Number of continents: {{answer2}} (Correct: 7)\n3. Is Earth flat?: {{answer3}} (Correct: no)\n\nNote: Automatic score calculation would require an external API call, as the template system does not support arithmetic operations."
                },
                "routes": [
                    {"condition": "true", "target_node": "end"}
                ],
                "position": {"x": 100, "y": 960}
            },
            "end": {
                "id": "end",
                "name": "End",
                "type": "END",
                "config": {
                    "type": "END"
                },
                "position": {"x": 450, "y": 700}
            }
        }
    }


def get_appointment_booking_flow():
    """
    Example Flow 5: Appointment Booking System

    Demonstrates:
    - MENU with dynamic options from array variable
    - output_mapping to extract selected slot details
    - PROMPT with validation for contact info
    - API_ACTION with POST request (submit booking)
    - Template variables in API request body
    - Complete end-to-end workflow

    Trigger: BOOKING
    """
    return {
        "name": "Appointment Booking",
        "trigger_keywords": ["BOOKING"],
        "variables": {
            "available_slots": {"type": "ARRAY", "default": [
                {"id": "slot1", "day": "Monday", "time": "9:00 AM", "doctor": "Dr. Smith"},
                {"id": "slot2", "day": "Monday", "time": "2:00 PM", "doctor": "Dr. Johnson"},
                {"id": "slot3", "day": "Tuesday", "time": "10:00 AM", "doctor": "Dr. Williams"},
                {"id": "slot4", "day": "Wednesday", "time": "3:00 PM", "doctor": "Dr. Brown"}
            ]},
            "selected_slot_id": {"type": "STRING", "default": ""},
            "selected_day": {"type": "STRING", "default": ""},
            "selected_time": {"type": "STRING", "default": ""},
            "selected_doctor": {"type": "STRING", "default": ""},
            "customer_name": {"type": "STRING", "default": ""},
            "customer_phone": {"type": "STRING", "default": ""}
        },
        "start_node_id": "welcome",
        "nodes": {
            "welcome": {
                "id": "welcome",
                "name": "Welcome",
                "type": "MESSAGE",
                "config": {
                    "type": "MESSAGE",
                    "text": "Hello! I can help you book an appointment. Here are the available time slots."
                },
                "routes": [
                    {"condition": "true", "target_node": "select_slot"}
                ],
                "position": {"x": 100, "y": 200}
            },
            "select_slot": {
                "id": "select_slot",
                "name": "Select Slot",
                "type": "MENU",
                "config": {
                    "type": "MENU",
                    "text": "Which time slot works best for you?",
                    "source_type": "DYNAMIC",
                    "source_variable": "available_slots",
                    "item_template": "{{item.day}} at {{item.time}} with {{item.doctor}}",
                    "output_mapping": [
                        {"source_path": "id", "target_variable": "selected_slot_id"},
                        {"source_path": "day", "target_variable": "selected_day"},
                        {"source_path": "time", "target_variable": "selected_time"},
                        {"source_path": "doctor", "target_variable": "selected_doctor"}
                    ],
                    "error_message": "Invalid selection. Please enter a number corresponding to one of the available appointment slots."
                },
                "routes": [
                    {"condition": "true", "target_node": "ask_name"}
                ],
                "position": {"x": 100, "y": 420}
            },
            "ask_name": {
                "id": "ask_name",
                "name": "Ask Name",
                "type": "PROMPT",
                "config": {
                    "type": "PROMPT",
                    "text": "Perfect! What's your full name?",
                    "save_to_variable": "customer_name"
                },
                "routes": [
                    {"condition": "true", "target_node": "ask_phone"}
                ],
                "position": {"x": 480, "y": 420}
            },
            "ask_phone": {
                "id": "ask_phone",
                "name": "Ask Phone",
                "type": "PROMPT",
                "config": {
                    "type": "PROMPT",
                    "text": "And what's your phone number?",
                    "save_to_variable": "customer_phone",
                    "validation": {
                        "type": "EXPRESSION",
                        "rule": "input.isNumeric() && input.length >= 10",
                        "error_message": "Please enter a valid phone number with at least 10 digits."
                    }
                },
                "routes": [
                    {"condition": "true", "target_node": "submit_booking"}
                ],
                "position": {"x": 860, "y": 420}
            },
            "submit_booking": {
                "id": "submit_booking",
                "name": "Submit Booking",
                "type": "API_ACTION",
                "config": {
                    "type": "API_ACTION",
                    "request": {
                        "method": "POST",
                        "url": "https://jsonplaceholder.typicode.com/posts",
                        "headers": [
                            {"name": "Content-Type", "value": "application/json"}
                        ],
                        "body": "{\"slot_id\": \"{{selected_slot_id}}\", \"day\": \"{{selected_day}}\", \"time\": \"{{selected_time}}\", \"doctor\": \"{{selected_doctor}}\", \"name\": \"{{customer_name}}\", \"phone\": \"{{customer_phone}}\"}"
                    }
                },
                "routes": [
                    {"condition": "success", "target_node": "booking_success"},
                    {"condition": "error", "target_node": "booking_failed"}
                ],
                "position": {"x": 100, "y": 660}
            },
            "booking_success": {
                "id": "booking_success",
                "name": "Booking Success",
                "type": "MESSAGE",
                "config": {
                    "type": "MESSAGE",
                    "text": "Excellent! Your appointment has been booked successfully.\n\nAppointment Details:\nDay: {{selected_day}}\nTime: {{selected_time}}\nDoctor: {{selected_doctor}}\nName: {{customer_name}}\nPhone: {{customer_phone}}\n\nYou'll receive a confirmation message shortly."
                },
                "routes": [
                    {"condition": "true", "target_node": "end"}
                ],
                "position": {"x": 600, "y": 640}
            },
            "booking_failed": {
                "id": "booking_failed",
                "name": "Booking Failed",
                "type": "MESSAGE",
                "config": {
                    "type": "MESSAGE",
                    "text": "I'm sorry, but I wasn't able to complete your booking at this time. Please try again later or contact us directly."
                },
                "routes": [
                    {"condition": "true", "target_node": "end"}
                ],
                "position": {"x": 600, "y": 820}
            },
            "end": {
                "id": "end",
                "name": "End",
                "type": "END",
                "config": {
                    "type": "END"
                },
                "position": {"x": 2350, "y": 200}
            }
        }
    }


def get_all_example_flows():
    """
    Get all example flows

    Returns:
        List of flow definitions ready to be created
    """
    return [
        get_customer_support_menu_flow(),
        get_onboarding_form_flow(),
        get_weather_lookup_flow(),
        get_quiz_flow(),
        get_appointment_booking_flow()
    ]
