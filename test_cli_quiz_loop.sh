#!/bin/bash
# Test script to verify session expiry handling

echo "Testing CLI with looping logic (answer 'no' first, then 'yes' twice)..."
echo -e "2\n1\n1" | docker exec -i pyquizhub-api-1 poetry run python -m pyquizhub.adapters.cli.user_cli start --user-id cli_loop_test_$(date +%s) --token AVOKNQW61EIYHZD7
