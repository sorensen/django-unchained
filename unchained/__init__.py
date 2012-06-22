
import re
import logging

from django.conf import settings
from django.db import models

import utils

log = logging.getLogger(__name__)

__version__ = '0.0.1'
__authors__ = [
    'Beau Sorensen <mail@beausorensen.com>'
]
__all__ = (
    'ENABLE_INJECTION', 'ENABLE_INTEGRATION', 'InjectIntegrateManager', 'InjectIntegrateModel', 
    'InjectIntegrateQuerySet', 'InjectionManager', 'InjectionModel', 'InjectionQuerySet', 
    'IntegrationManager', 'IntegrationModel', 'IntegrationQuerySet', 'UnchainedManager', 
    'UnchainedModel', 'UnchainedQuerySet', '__version__', '__authors__'
)

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

ENABLE_INTEGRATION = getattr(settings, 'UNCHAINED_ENABLE_INTEGRATION', True)
ENABLE_INJECTION   = getattr(settings, 'UNCHAINED_ENABLE_INJECTION', True)


# ---------------------------------------------------------------------
# Django unchained modeling
# ---------------------------------------------------------------------

class UnchainedQuerySet(models.query.QuerySet):
    '''
    Repeat of the default django queryset, in a more abstract class, converts
    all args and kwargs before sending to the base queryset methods for easy
    transformation
    '''
    def _args(self, *args):
        return args

    def _kwargs(self, **kwargs):
        return kwargs

    # Default method overrides
    # -----------------------------------------------------

    def aggregate(self, *args, **kwargs):
        return super(UnchainedQuerySet, self).aggregate(*self._args(*args), **self._kwargs(**kwargs))

    def count(self, *args, **kwargs):
        return super(UnchainedQuerySet, self).count(*self._args(*args), **self._kwargs(**kwargs))

    def get(self, *args, **kwargs):
        return super(UnchainedQuerySet, self).get(*self._args(*args), **self._kwargs(**kwargs))

    def create(self, *args, **kwargs):
        return super(UnchainedQuerySet, self).create(**self._kwargs(**kwargs))

    def get_or_create(self, *args, **kwargs):
        return super(UnchainedQuerySet, self).get_or_create(**self._kwargs(**kwargs))

    def latest(self, *args, **kwargs):
        return super(UnchainedQuerySet, self).latest(*self._args(*args), **self._kwargs(**kwargs))

    def in_bulk(self, *args, **kwargs):
        return super(UnchainedQuerySet, self).in_bulk(*self._args(*args), **self._kwargs(**kwargs))

    def delete(self, *args, **kwargs):
        return super(UnchainedQuerySet, self).delete(*self._args(*args), **self._kwargs(**kwargs))

    def update(self, *args, **kwargs):
        return super(UnchainedQuerySet, self).update(*self._args(*args), **self._kwargs(**kwargs))

    def exists(self, *args, **kwargs):
        return super(UnchainedQuerySet, self).exists(*self._args(*args), **self._kwargs(**kwargs))

    def values(self, *args, **kwargs):
        return super(UnchainedQuerySet, self).values(*self._args(*args), **self._kwargs(**kwargs))

    def values_list(self, *args, **kwargs):
        return super(UnchainedQuerySet, self).values_list(*self._args(*args), **self._kwargs(**kwargs))

    def filter(self, *args, **kwargs):
        return super(UnchainedQuerySet, self).filter(*self._args(*args), **self._kwargs(**kwargs))

    def exclude(self, *args, **kwargs):
        return super(UnchainedQuerySet, self).exclude(*self._args(*args), **self._kwargs(**kwargs))

    def select_related(self, *fields, **kwargs):
        return super(UnchainedQuerySet, self).select_related(*self._args(*fields), **self._kwargs(**kwargs))

    def annotate(self, *args, **kwargs):
        return super(UnchainedQuerySet, self).annotate(*self._args(*args), **self._kwargs(**kwargs))

    def order_by(self, *field_names):
        return super(UnchainedQuerySet, self).order_by(*self._args(*field_names))

    def defer(self, *fields):
        return super(UnchainedQuerySet, self).defer(*self._args(*fields))

    def only(self, *fields):
        return super(UnchainedQuerySet, self).only(*self._args(*fields))


class UnchainedManager(models.Manager):
    def get_query_set(self):
        return UnchainedQuerySet(self.model, using=self._db)


class UnchainedModel(models.Model):
    objects = UnchainedManager()

    class Meta:
        abstract = True


# ---------------------------------------------------------------------
# Integration package
# ---------------------------------------------------------------------

class IntegrationQuerySet(UnchainedQuerySet):
    IGNORE = [
        'gt', 'gte', 'lt', 'lte', 'range', 'in', 'isnull', 'pk',
        'contains', 'icontains', 'exact', 'iexact', 'iregex',
        'startswith', 'istartswith', 'endswith', 'iendswith',
        'year', 'month', 'day', 'week_day', 'search', 'regex', 'defaults'
    ]
    # Map the given field (key) and get its dynamic value
    def _map_field(self, klass, key):
        return klass.get_field_mapper(key=key)

    def _convert_key(self, key, level=6):
        parts = key.split('__')
        for part in parts:
            if part in self.IGNORE:
                parts.remove(part)
        
        klass = self.model
        for part in parts:
            index = parts.index(part) + 1
            part = part.replace('-', '')
            try:
                field = klass._meta.get_field_by_name(part)[0]
            except models.fields.FieldDoesNotExist, e:
                mapper = getattr(klass, 'FIELD_MAP', {})
                if part not in mapper:
                    log.warning('Field not found: %s -> %s' % (part, klass))
                    raise e

                mapped = mapper.get(part)
                new = key.replace(part, mapped)
                if mapped.find('__') == 0:
                    new = key.replace(part, klass.get_field_mapper(key=part))
                caller = utils.get_caller(level=level)
                log.debug('[%s] Field mapped: %s => %s' % (caller, key, new))
                return new

            # The order of these checks is important
            if getattr(field, 'rel', False):
                klass = field.rel.to
            elif hasattr(field, 'model'):
                klass = field.model
            else:
                raise Exception

        return self._check_mapper(klass=klass, key=key)

    # Transform Q() arguments
    def _args(self, *args):
        def convert(query, level=8):
            if not hasattr(query, 'children'):
                return (self._convert_key(key=query),)
            
            tmp = []
            for child in query.children:
                if isinstance(child, models.Q):
                    convert(query=child, level=level + 1)
                    tmp.append(child)
                else:
                    d = dict((child,))
                    for key in d:
                        new = key
                        val = d[key]
                        new = self._convert_key(key=key, level=level)
                        tmp.append((new, val))

            query.children = tmp
            return (query,)

        if ENABLE_INTEGRATION:
            try:
                tmp = ()
                for arg in args:
                    tmp += convert(query=arg)
                return super(IntegrationQuerySet, self)._args(*tmp)
            except Exception, e:
                log.exception('Arg conversion failed')
                if settings.DEBUG:
                    raise e
        return super(IntegrationQuerySet, self)._args(*args)

    # Transform a given kwarg dictionary to the correct mapped values
    def _kwargs(self, **kwargs):
        if ENABLE_INTEGRATION:
            try:
                imkwargs = {}
                for key in kwargs:
                    new = key
                    val = kwargs.get(key)
                    new = self._convert_key(key=key)
                    imkwargs[new] = val
                return super(IntegrationQuerySet, self)._kwargs(**imkwargs)
            except Exception, e:
                log.exception('Kwarg conversion failed: %s', str(kwargs))
                if settings.DEBUG:
                    raise e
        return super(IntegrationQuerySet, self)._kwargs(**kwargs)

    # Look through all field mapper entries to see if we have a match
    def _has_match(self, klass, key):
        fields = getattr(klass, 'FIELD_MAP', {})
        for field in fields:
            exps = [
                r'__%s+$' % field,
                r'__%s+__$' % field,
                r'^%s+' % field
            ]
            if re.match('|'.join(exps), key):
                return field, fields.get(field)
        return None, None

    def _check_mapper(self, klass, key):
        m, mapped = self._has_match(klass=klass, key=key)
        if m:
            # Replace map value dynamically from model if value starts with '__'
            if mapped.find('__') == 0:
                return key.replace(m, self._map_field(key=m))
            return mapped
        return key


class IntegrationManager(UnchainedManager):
    def get_query_set(self):
        return IntegrationQuerySet(self.model, using=self._db)


class IntegrationModel(UnchainedModel):
    FIELD_MAP = {}

    objects = IntegrationManager()

    @classmethod
    def get_field_mapper(self, key):
        if key in self.FIELD_MAP:
            return self.FIELD_MAP.get(key)
        return key

    class Meta:
        abstract = True


# ---------------------------------------------------------------------
# Injection module
# ---------------------------------------------------------------------

class InjectionQuerySet(UnchainedQuerySet):
    # Injection map on patterns to look for and the coorosponding field to use
    # for the query injection, if field begins with __, it is considered dynamic
    # and will call the model to get the prefix for it, the search key will be used
    # to ask the model for the correct value to inject into the query
    #
    #   {`key_to_search` : `field_to_use`}
    #
    def _inject(self, *args, **kwargs):
        found = False
        def check(query, seek):
            for child in getattr(query, 'children', []):
                if isinstance(child, models.Q):
                    return check(query=child)
                else:
                    d = dict((child,))
                    for key in d:
                        if not not ~key.find(seek):
                            return True
            return False

        if ENABLE_INJECTION:
            mapping = getattr(self.model, 'INJECTION_MAP', {})
            for seek in mapping:
                replace = mapping.get(seek)

                for arg in args:
                    found = check(query=arg, seek=seek)
                    if found:
                        break

                for key in kwargs:
                    if not not ~key.find(seek):
                        found = True
                        break

                if not found:
                    value = self.model.get_injection_value(field=seek)

                    if replace.find('__') == 0:
                        key = '%s%s' % (self.model.get_injection_prefix(), replace)
                    else:
                        key = replace

                    # Kwargs have a higher priority, only use args if they were used instead
                    if args and not kwargs:
                        args += (models.Q(**{key: value}),)
                    else:
                        kwargs[key] = value
                    
                    caller = utils.get_caller(level=5)
                    log.debug('[%s] Query injected: %s = %s' % (caller, key, value))

        return args, kwargs

    def get(self, *args, **kwargs):
        args, kwargs = self._inject(*args, **kwargs)
        return super(InjectionQuerySet, self).get(*args, **kwargs)

    def get_or_create(self, *args, **kwargs):
        args, kwargs = self._inject(*args, **kwargs)
        return super(InjectionQuerySet, self).get_or_create(**kwargs)
    
    def filter(self, *args, **kwargs):
        args, kwargs = self._inject(*args, **kwargs)
        return super(InjectionQuerySet, self).filter(*args, **kwargs)


class InjectionManager(UnchainedManager):
    def get_query_set(self):
        return InjectionQuerySet(self.model, using=self._db)


class InjectionModel(UnchainedModel):
    INJECTION_MAP = {}

    objects = InjectionManager()

    @classmethod
    def get_injection_prefix(self):
        return ''

    @classmethod
    def get_injection_value(self, field):
        return ''

    class Meta:
        abstract = True


# ---------------------------------------------------------------------
# Combine both injection and integration modules
# ---------------------------------------------------------------------

class InjectIntegrateQuerySet(InjectionQuerySet, IntegrationQuerySet):
    pass

class InjectIntegrateManager(InjectionManager, IntegrationManager):
    def get_query_set(self):
        return InjectIntegrateQuerySet(self.model, using=self._db)

class InjectIntegrateModel(InjectionModel, IntegrationModel):
    objects = InjectIntegrateManager()

    class Meta:
        abstract = True


