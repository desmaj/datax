import csv
import sys
from xml.etree import ElementTree as ET

import click


class FieldExtractor(object):

    @classmethod
    def from_spec(cls, field_spec):
        field_spec_parts = field_spec.split(':')
        value_source = field_spec_parts.pop(0)
        field_name = field_spec_parts.pop(0)
        if field_spec_parts:
            field_format = field_spec_parts.pop(0)
        else:
            field_format = None
        if value_source not in ['attrib', 'text']:
            raise ValueError("Invalid value source: {}".format(value_source))
        return FieldExtractor(value_source, field_name, field_format)

    def __init__(self, source, name, field_format=None):
        self._source = source
        self._name = name
        if field_format is None:
            self._formatter = str
        else:
            format_spec = ''.join(['{:', field_format, '}'])
            self._formatter = format_spec.format

    @property
    def name(self):
        return self._name

    def extract(self, element):
        if self._source == 'attrib':
            value = element.get(self._name)
        elif self._source == 'text':
            child = element.find(self._name)
            if child is not None:
                value = child.text
            else:
                raise KeyError(self._name)
        return self._formatter(value)


class XMLDocTransformer(object):

    def __init__(self, index_field, field_specs, root_path=None):
        self._index_field = index_field
        self._fields = [
            FieldExtractor.from_spec(field_spec)
            for field_spec in field_specs
        ]
        if root_path and not root_path.startswith('.//'):
            root_path = './/{}'.format(root_path)
        self._root_path = root_path

    @property
    def index_field(self):
        return self._index_field_name

    def field_names(self):
        return [self._index_field] + [field.name for field in self._fields]

    def transform(self, xmldoc):
        root = xmldoc.getroot()
        if self._root_path is not None:
            root = root.find(self._root_path)

        items = []
        for index, item in enumerate(root):
            item_dict = {self._index_field: index}
            item_dict.update(
                {
                    field.name: field.extract(item)
                    for field in self._fields
                }
            )
            items.append(item_dict)

        return items


@click.command()
@click.argument(
    'infile',
    type=click.Path(),
)
@click.argument(
    'data_fields',
    type=str,
    nargs=-1,
)
@click.option(
    '--index-field',
    type=str,
    default='ID',
    help="The name of the ID field (the index in the sequence).",
)
@click.option(
    '--root-path',
    type=str,
    default=None,
    help="An XPath expression describing the root element of the sequence.",
)
def main(infile, data_fields, index_field, root_path):
    """ Extract a sequence of homogenseous elements as tabular data.

        INFILE is the path to the source XML document.

        FIELDS is a number of field specifications.

        Field specifications come in the form: '<source>:<name>:<format>'.\n
            - <source> is either 'attrib' (the value is an attribute of the
        element), or 'text' (the value is the text of a child element).\n
            - <name> is either an attribute name or a child element tag,
        respectively.\n
            - <format> is a formatting spec in the Python string formatting
        mini-language
        https://docs.python.org/3.4/library/string.html#formatspec.

      Examples:

        In the following example, the XML document is called
        'election_definition.xml' and we want to extract some children of the
        'reg_areas' element into a CSV. We want to include the text of the child
        tag 'x' and the text of the child tag 'y'.

        $ python transform.py election_definition.xml --root-path //reg_areas\\
      \b\b      text:x:.5s text:y:.5s


    """
    input_document = ET.parse(infile)

    transformer = XMLDocTransformer(index_field, data_fields, root_path)
    tabledata = transformer.transform(input_document)

    fields = transformer.field_names()

    outcsv = csv.DictWriter(sys.stdout, fields)
    outcsv.writeheader()
    outcsv.writerows(tabledata)


if __name__ == '__main__':
    main()
