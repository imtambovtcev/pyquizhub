#!/bin/bash
# Test script to automate CLI quiz interaction

# Simulate answering "yes" to both questions
echo -e "1\n1" | docker exec -i pyquizhub-api-1 poetry run python -m pyquizhub.adapters.cli.user_cli start --user-id cli_test_user_$(date +%s) --token AVOKNQW61EIYHZD7
