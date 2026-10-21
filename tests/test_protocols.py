"""Offline compatibility checks for modern protobuf bindings."""
# Protobuf creates its public message/enum classes dynamically.
# pylint: disable=no-name-in-module,no-member
import hashlib
import importlib
import json
from pathlib import Path
import unittest

from google.protobuf import descriptor_pb2, json_format, message_factory
from librespot.proto import Metadata_pb2 as Metadata
from librespot.proto.Authentication_pb2 import AuthenticationType, LoginCredentials
from librespot.proto.ExtendedMetadata_pb2 import BatchedEntityRequest, EntityRequest, ExtensionQuery
from librespot.proto.ExtensionKind_pb2 import ExtensionKind


def normalized_schema(value):
    """Ignore generated JSON aliases while preserving every wire definition."""
    if isinstance(value, dict):
        return {key: normalized_schema(item) for key, item in value.items() if key != 'json_name'}
    if isinstance(value, list):
        return [normalized_schema(item) for item in value]
    return value


class ProtocolTests(unittest.TestCase):
    """Check every generated schema and representative protocol messages."""

    def test_all_protocol_modules_preserve_original_schemas(self):
        """The compiler update must not alter message fields or enum values."""
        expected = json.loads(Path(__file__).with_name('protocol-schema-sha256.json').read_text())
        root = Path(__file__).resolve().parents[1] / 'librespot' / 'proto'
        observed = {}
        for path in root.rglob('*_pb2.py'):
            module = importlib.import_module('librespot.proto.' + '.'.join(path.relative_to(root).with_suffix('').parts))
            schema = descriptor_pb2.FileDescriptorProto.FromString(module.DESCRIPTOR.serialized_pb)
            normalized = normalized_schema(json_format.MessageToDict(schema, preserving_proto_field_name=True))
            observed[schema.name] = hashlib.sha256(json.dumps(normalized, sort_keys=True).encode()).hexdigest()
        self.assertEqual(observed, expected)

    def test_all_message_classes_support_binary_round_trips(self):
        """Import and construct nested classes as well as top-level messages."""
        root = Path(__file__).resolve().parents[1] / 'librespot' / 'proto'
        count = 0

        def check(descriptor):
            nonlocal count
            cls = message_factory.GetMessageClass(descriptor)
            message = cls()
            self.assertEqual(cls.FromString(message.SerializePartialToString()), message)
            count += 1
            for nested in descriptor.nested_types:
                check(nested)

        for path in root.rglob('*_pb2.py'):
            module = importlib.import_module('librespot.proto.' + '.'.join(path.relative_to(root).with_suffix('').parts))
            for descriptor in module.DESCRIPTOR.message_types_by_name.values():
                check(descriptor)
        self.assertGreater(count, 100)

    def test_metadata_json_and_binary_round_trips(self):
        """Track/disc fields survive the runtime and generated-code upgrade."""
        track = Metadata.Track(gid=b'\x01' * 16, name='Fixture', duration=123000,
                               number=3, disc_number=2)
        album = Metadata.Album(name='Release')
        album.disc.add(number=2).track.add().CopyFrom(track)
        data = json_format.MessageToDict(album, preserving_proto_field_name=True)
        restored = json_format.ParseDict(data, Metadata.Album())
        self.assertEqual(restored, album)
        self.assertEqual(Metadata.Album.FromString(album.SerializeToString()), album)
        self.assertEqual(restored.disc[0].track[0].disc_number, 2)

    def test_authentication_and_batch_requests_serialize(self):
        """Exercise local message construction without sending an account request."""
        credentials = LoginCredentials(username='fixture', auth_data=b'not-a-token',
                                       typ=AuthenticationType.AUTHENTICATION_STORED_SPOTIFY_CREDENTIALS)
        self.assertEqual(LoginCredentials.FromString(credentials.SerializeToString()), credentials)
        request = BatchedEntityRequest(entity_request=[
            EntityRequest(entity_uri='spotify:track:0000000000000000000001',
                          query=[ExtensionQuery(extension_kind=ExtensionKind.TRACK_V4)])])
        self.assertEqual(BatchedEntityRequest.FromString(request.SerializeToString()), request)


if __name__ == '__main__':
    unittest.main()
