# Django Unchained

Provides an easier way of overriding Django's default QuerySet, by default allowing you to tap into
the args and kwargs of any QuerySet method without overriding them all. The package also provides an
integration manager and injection manager for re-mapping queries sent to the ORM, or forcing all queries
to contain a certain constraint. Unchain your Django app!


## Installation

```bash
pip install django-unchained
````

Alternatively, you can download the project and put the `client_errors` directory into 
your project directory.

Add the following app to your project's `INSTALLED_APPS` in the `settings.py` file:

````
'unchained',
````


## Configuration

* `UNCHAINED_ENABLE_INTEGRATION` enable ORM field mapping (optional, default `True`)
* `UNCHAINED_ENABLE_INJECTION` enable ORM query injection (optional, default `True`)


## Usage

By having any model inherit from the `unchained.IntegrationModel`, you can specify a `FIELD_MAP`
dict attribute on the model, telling the ORM what fields to automatically map to another. This may 
also be done dynamically if the value to any key begins with a `__`, which will then call to the 
model's `get_field_mapper` method to get the correct field.

```python
from django import models
import unchained

class Foo(unchained.IntegrationModel):
    FIELD_MAP = {
        'old' : 'new',
        'blah' : '__hey__there'
    }
    @classmethod
    def get_field_mapper(self, field):
        return 'dynamically%s' % self.FIELD_MAP.get(field)
````

The `unchained.InjectionModel` will behave similarly, the model will need a `INJECTION_MAP` 
dict attribute to tell the ORM what to look for.  The key represents the field, or partial field,
to look for (since it may represent a variety of options), and the value represents the actual
field to use.  If the value begins with a `__`, a prefix will be added by calling the model's 
`get_injection_prefix` method. It will always call a `get_injection_value` method on the model 
to find out what value should be used for the query.

```python
class Bar(unchained.InjectionModel):
    INJECTION_MAP = {
        'search' : 'actual_search_field',
        'partial' : '__dont_know__yet'
    }
    @classmethod
    def get_injection_prefix(self):
        return 'icouldbedynamic'

    @classmethod
    def get_injection_value(self, field):
        if field == 'search':
            return 3
        elif field == 'partial':
            return 'heeeeeey'
        raise Exception
````

Both classes can be combined using the `unchained.InjectIntegrateModel`

If you would like to override the base `unchained.UnchainedModel`, `unchained.UnchainedQuerySet`, 
or `unchained.UnchainedManager`, you will need to replace all three. (sorry, its a Django thing).
You can also set a models `objects` directly to your custom manager and then not need to override
the model itself. I tend to inherit from the custom model class as to save myself from repeating 
too much code. But its up to you.

```python
import unchained

class SpecialQuerySet(unchained.UnchainedQuerySet)
    def _kwargs(self, **kwargs):
        # do something to the kwargs
        return kwargs

    def _args(self, *args):
        # do something to the args
        return args

class SpecialManager(unchained.UnchainedManager):
    def get_query_set(self):
        return SpecialQuerySet(self.model, using=self._db)

# Optional
class SpecialModel(unchained.Model):
    objects = SpecialManager()

    class Meta:
        abstract = True
````


## License

(The MIT License)

Copyright (c) 2011-2012 Beau Sorensen <mail@beausorensen.com>

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
'Software'), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
