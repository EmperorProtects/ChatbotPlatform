#!/bin/bash

curl -X GET -H "Content-Type: application/json" \
  -d '{    
    "brief_id": 1,
    "metadata_filters": {
        "type": "system_prompt"
    }}' \
  http://localhost:8006/search/by_metadata

curl -X POST -H "Content-Type: application/json" \
  -d '{
    
}' \
  http://localhost:8006/business/brie
