#!/bin/bash

# Start Ollama in the background.
/bin/ollama serve &
# Record Process ID.
pid=$!

# Pause for Ollama to start.
sleep 5

echo "🔴 Retrieve LLAMA3 model..."
ollama pull llama3.2
echo "Retrieving LLAMA3 model... 🟢 Done!"

echo "🔴 Retrieve nomic model..."
ollama pull nomic-embed-text
echo "🟢 Done!"

# Wait for Ollama process to finish.
wait $pid
