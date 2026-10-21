# Offline protocol checks

Run `python -m unittest discover -s tests -v` with the project dependencies.
No account, session or network request is created.

The SHA-256 manifest records the original 35 compiled schemas at upstream commit
`01abfc8ad012dbc40e90417e640faaf271ea2f98`, normalized as JSON with generated
`json_name` aliases excluded. Regeneration must preserve those hashes.

`python dev/regenerate_protos.py` uses protoc 36.1 and preserves CamelCase public
module names and package-local imports. Python gencode 7.36.1 is tested with
protobuf 7.36.2's normal upb backend.
