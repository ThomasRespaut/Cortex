import json

tools_file_path = "../../../assistant/tools.json"
with open(tools_file_path, "r", encoding="utf-8") as file:
    tools_data = json.load(file)

# Transform the tools structure into question/response pairs
transformed_data = []
for tool in tools_data:
    func_name = tool["function"]["name"]
    func_desc = tool["function"]["description"]
    func_params = tool["function"].get("parameters", {}).get("properties", {})

    # Example question
    question = f"{func_desc}"

    # Example response
    params_example = []
    for param, details in func_params.items():
        if details["type"] == "integer":
            params_example.append(f"{param}=10")
        elif details["type"] == "string":
            params_example.append(f"{param}='example'")
        elif details["type"] == "array":
            params_example.append(f"{param}=['value1', 'value2']")

    response = f"[{func_name} {' '.join(params_example)}]" if params_example else f"[{func_name}]"

    # Append the transformed structure
    transformed_data.append({"question": question, "response": response})

# Save the transformed data to a new JSON file
output_transformed_path = "tools_transformed.json"
with open(output_transformed_path, "w", encoding="utf-8") as output_file:
    json.dump(transformed_data, output_file, ensure_ascii=False, indent=4)


