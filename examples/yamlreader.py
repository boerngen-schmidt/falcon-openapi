import falconopenapi as fo

definition = fo.OpenApiDefinition("petstore-expanded.yaml")

for path in definition.paths:
    print(path)
