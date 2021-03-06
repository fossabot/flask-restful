from flask_restful import reqparse

from models import Field, ApiDataType, BaseModel
from exceptions.exceptions import InvalidArgumentException


class QueryField(Field):
    __slots__ = ('name', 'field_type', 'mock_func', 'enum_values', 'description', 'nullable', 'required',
                 'location', 'default', 'parser_kwargs', 'parse_func')

    def __init__(self, field_type: ApiDataType, location, parser_func=None, required=False, mock_func=False,
                 enum_values: tuple = (), comment="", nullable=True, **kwargs):
        super().__init__(field_type, mock_func, enum_values, comment, nullable)
        self.location = location
        self.parser_kwargs = kwargs
        self.required = required
        self.parse_func = parser_func
        if 'default' in kwargs:
            self.default = kwargs['default']


class BaseQueryModel(BaseModel):

    def __init__(self, **kwargs):
        super().__init__(drop_missing=False, **kwargs)
        self.__storage__ = kwargs
        for field_name in self.__fields_map__.keys():
            if field_name not in self.__storage__:
                delattr(self, field_name)

    @classmethod
    def parse_args(cls):
        parser = reqparse.RequestParser()

        for field in cls.__fields__:
            parser.add_argument(field.name, type=field.parse_func, location=field.location, required=field.required,
                                nullable=field.nullable, **field.kwargs)
        parsed = parser.parse_args()

        for field in cls.__fields__:
            if field.enum_values and field.name in parsed:
                value = parsed[field.name]
                if value is not None and value not in field.enum_values:
                    raise InvalidArgumentException("参数 [{}] 的值必须在 [{}] 中".format(field.name, field.enum_values))

        instance = cls(**parsed)
        return instance

    def as_dict(self):
        return self.__storage__

    def get(self, item, default=None):
        return self.__storage__.get(item, default)

    def __contains__(self, item):
        return item in self.__storage__

    def __str__(self):
        return '[<{}>: \n{}]'.format(self.__class__.__name__, pprint.pformat(self.__storage__, indent=4))


class NoArgs(BaseQueryModel):
    pass
