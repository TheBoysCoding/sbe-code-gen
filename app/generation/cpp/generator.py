# Copyright (C) 2022 Sergey Kovalevich <inndie@gmail.com>
# This file may be distributed under the terms of the GNU GPLv3 license

from jinja2 import Environment, FileSystemLoader
import pathlib
import os

from app.generator import GeneratorBase

class Generator(GeneratorBase):
    def __init__(self, path: str) -> None:
        self.path = path
        self.env = Environment(
            loader = FileSystemLoader(f'{pathlib.Path(__file__).parent.resolve()}/templates'),
            autoescape = False,
            trim_blocks = True,
            lstrip_blocks = True,
            keep_trailing_newline = True
        )
        self.addFilters()

    def _generateImpl(self, schema: dict) -> None:
        self.ensurePathExists()

        for encodedType in schema['types']:
            documentName = self.makeDocumentName(encodedType['name'])
            if encodedType['token'] == 'type':
                pass
            elif encodedType['token'] == 'composite':
                self.generateDocument(documentName, 'composite.tmpl', type = encodedType, schema = schema,
                                      includes = self.generateIncludesForComposite(encodedType))
            elif encodedType['token'] == 'enum':
                self.generateDocument(documentName, 'enum.tmpl', type = encodedType, schema = schema)
            elif encodedType['token'] == 'set':
                self.generateDocument(documentName, 'set.tmpl', type = encodedType, schema = schema)

        for message in schema['messages']:
            documentName = self.makeDocumentName(message['name'])
            self.generateDocument(documentName, 'message.tmpl', message = message, schema = schema,
                                  includes = self.generateIncludesForMessage(message, schema))

        self.generateDocument('schema.h', 'schema.tmpl', schema = schema, includes = self.generateIncludes(schema))

    def makeDocumentName(self, name: str) -> str:
        return self.env.filters['format_class_name'](name) + '.h'

    def generateDocument(self, documentName: str, templateName: str, **kwargs) -> None:
        template = self.env.get_template(templateName)
        documentPath = f'{self.path}/{documentName}'
        documentContent = template.render(**kwargs)
        with open(documentPath, mode = 'w', encoding = 'utf8') as document:
            document.write(documentContent)

    def generateIncludesForMessage(self, message: dict, schema: dict = None) -> list:
        includes = set()
        for field in message['fields']:
            if field['token'] == 'field':
                if field['type']['token'] in ('composite', 'enum', 'set'):
                    includes.add(self.makeDocumentName(field['type']['name']))
            elif field['token'] == 'group':
                includes.add(self.makeDocumentName(field['dimensionType']['name']))
                # this func could be used for iterate over group fields
                includes = includes.union(self.generateIncludesForMessage(field))
            elif field['token'] == 'data':
                includes.add(self.makeDocumentName(field['type']['name']))

        if schema != None:
            includes.add(self.makeDocumentName(schema['headerType']['name']))

        return list(includes)

    def generateIncludesForComposite(self, composite: dict) -> list:
        includes = set()
        for field in composite['containedTypes']:
            if field['token'] in ('composite', 'enum', 'set'):
                includes.add(self.makeDocumentName(field['type']['name']))

        return list(includes)

    def generateIncludes(self, schema: dict) -> list:
        includes = set()
        for message in schema['messages']:
            includes.add(self.makeDocumentName(message['name']))

        return list(includes)

    def ensurePathExists(self) -> None:
        if not os.path.exists(self.path):
            os.makedirs(self.path)

    def addFilters(self) -> None:
        self.env.filters['format_class_name'] = lambda value: value[0].upper() + value[1:]
        self.env.filters['format_method_name_get'] = lambda value: value[0].lower() + value[1:]
        self.env.filters['format_method_name_set'] = lambda value: value[0].lower() + value[1:]
        self.env.filters['format_method_name_is_present'] = lambda value: 'is' + value[0].upper() + value[1:] + 'Present'
        self.env.filters['format_method_name_reset'] = lambda value: value[0].lower() + value[1:] + 'Reset'
        self.env.filters['format_method_name_length'] = lambda value: value[0].lower() + value[1:] + 'Length'
        self.env.filters['format_method_name_get_count'] = lambda value: value[0].lower() + value[1:] + 'Count'
        self.env.filters['format_constant_name'] = lambda value: 'k' + value[0].upper() + value[1:]
        self.env.filters['replace_keyword']  = Generator.filterReplaceKeword

    @staticmethod
    def filterReplaceKeword(value: str) -> str:
        return {
            'int8':         'std::int8_t',
            'int16':        'std::int16_t',
            'int32':        'std::int32_t',
            'int64':        'std::int64_t',
            'uint8':        'std::uint8_t',
            'uint16':       'std::uint16_t',
            'uint32':       'std::uint32_t',
            'uint64':       'std::uint64_t',
            'CHAR_NULL':    '0',
            'CHAR_MIN':     '0x20',
            'CHAR_MAX':     '0x7e',
            'INT8_NULL':    'std::numeric_limits<std::int8_t>::min()',
            'INT8_MIN':     'std::numeric_limits<std::int8_t>::min() + 1',
            'INT8_MAX':     'std::numeric_limits<std::int8_t>::max()',
            'INT16_NULL':   'std::numeric_limits<std::int16_t>::min()',
            'INT16_MIN':    'std::numeric_limits<std::int16_t>::min() + 1',
            'INT16_MAX':    'std::numeric_limits<std::int16_t>::max()',
            'INT32_NULL':   'std::numeric_limits<std::int32_t>::min()',
            'INT32_MIN':    'std::numeric_limits<std::int32_t>::min() + 1',
            'INT32_MAX':    'std::numeric_limits<std::int32_t>::max()',
            'INT64_NULL':   'std::numeric_limits<std::int64_t>::min()',
            'INT64_MIN':    'std::numeric_limits<std::int64_t>::min() + 1',
            'INT64_MAX':    'std::numeric_limits<std::int64_t>::max()',
            'UINT8_NULL':   'std::numeric_limits<std::uint8_t>::max()',
            'UINT8_MIN':    'std::numeric_limits<std::uint8_t>::min()',
            'UINT8_MAX':    'std::numeric_limits<std::uint8_t>::max() - 1',
            'UINT16_NULL':  'std::numeric_limits<std::uint16_t>::max()',
            'UINT16_MIN':   'std::numeric_limits<std::uint16_t>::min()',
            'UINT16_MAX':   'std::numeric_limits<std::uint16_t>::max() - 1',
            'UINT32_NULL':  'std::numeric_limits<std::uint32_t>::max()',
            'UINT32_MIN':   'std::numeric_limits<std::uint32_t>::min()',
            'UINT32_MAX':   'std::numeric_limits<std::uint32_t>::max() - 1',
            'UINT64_NULL':  'std::numeric_limits<std::uint64_t>::max()',
            'UINT64_MIN':   'std::numeric_limits<std::uint64_t>::min()',
            'UINT64_MAX':   'std::numeric_limits<std::uint64_t>::max() - 1',
            'FLOAT_NULL':   'std::numeric_limits<float>::quiet_NaN()',
            'FLOAT_MIN':    'std::numeric_limits<float>::min()',
            'FLOAT_MAX':    'std::numeric_limits<float>::max()',
            'DOUBLE_NULL':  'std::numeric_limits<double>::quiet_NaN()',
            'DOUBLE_MIN':   'std::numeric_limits<double>::min()',
            'DOUBLE_MAX':   'std::numeric_limits<double>::max()'
        }.get(value, value)
