import unittest

from cornice.validators import colander_validator, colander_body_validator
from cornice.service import Service
from flex.core import validate

from cornice_swagger.swagger import CorniceSwagger, CorniceSwaggerException
from .support import GetRequestSchema, PutRequestSchema, response_schemas, BodySchema, HeaderSchema


class TestCorniceSwaggerGenerator(unittest.TestCase):

    def setUp(self):
        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            @service.get(validators=(colander_validator, ),
                         schema=GetRequestSchema(),
                         response_schemas=response_schemas)
            def view_get(self, request):
                """Serve ice cream"""
                return self.request.validated

            @service.put(validators=(colander_validator, ), schema=PutRequestSchema())
            def view_put(self, request):
                """Add flavour"""
                return self.request.validated

        self.service = service
        self.swagger = CorniceSwagger([self.service])
        self.spec = self.swagger('IceCreamAPI', '4.2')
        validate(self.spec)

    def test_path(self):
        self.assertIn('/icecream/{flavour}', self.spec['paths'])

    def test_path_methods(self):
        path = self.spec['paths']['/icecream/{flavour}']
        self.assertIn('get', path)
        self.assertIn('put', path)

    def test_path_parameters(self):
        parameters = self.spec['paths']['/icecream/{flavour}']['parameters']
        self.assertEquals(len(parameters), 1)
        self.assertEquals(parameters[0]['name'], 'flavour')

    def test_summary_docstrings(self):
        self.spec = self.swagger('IceCreamAPI', '4.2', summary_docstrings=True)
        validate(self.spec)
        summary = self.spec['paths']['/icecream/{flavour}']['get']['summary']
        self.assertEquals(summary, 'Serve ice cream')

    def test_with_schema_ref(self):
        swagger = CorniceSwagger([self.service], def_ref_depth=1)
        spec = swagger('IceCreamAPI', '4.2')
        self.assertIn('definitions', spec)

    def test_with_param_ref(self):
        swagger = CorniceSwagger([self.service], param_ref=True)
        spec = swagger('IceCreamAPI', '4.2')
        self.assertIn('parameters', spec)

    def test_with_resp_ref(self):
        swagger = CorniceSwagger([self.service], resp_ref=True)
        spec = swagger('IceCreamAPI', '4.2')
        self.assertIn('responses', spec)


class TestExtractContentTypes(unittest.TestCase):

    def test_json_renderer(self):

        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            @service.get(renderer='json')
            def view_get(self, request):
                return self.request.validated

        swagger = CorniceSwagger([service])
        spec = swagger('IceCreamAPI', '4.2')
        self.assertEquals(spec['paths']['/icecream/{flavour}']['get']['produces'],
                          ['application/json'])

    def test_xml_renderer(self):

        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            @service.get(renderer='xml')
            def view_get(self, request):
                return self.request.validated

        swagger = CorniceSwagger([service])
        spec = swagger('IceCreamAPI', '4.2')
        self.assertEquals(spec['paths']['/icecream/{flavour}']['get']['produces'],
                          ['text/xml'])

    def test_unkown_renderer(self):

        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            @service.get(renderer='')
            def view_get(self, request):
                return self.request.validated

        swagger = CorniceSwagger([service])
        spec = swagger('IceCreamAPI', '4.2')
        self.assertNotIn('produces', spec['paths']['/icecream/{flavour}']['get'])

    def test_single_ctype(self):

        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            @service.put(content_type='application/json')
            def view_put(self, request):
                return self.request.validated

        swagger = CorniceSwagger([service])
        spec = swagger('IceCreamAPI', '4.2')
        self.assertEquals(spec['paths']['/icecream/{flavour}']['put']['consumes'],
                          ['application/json'])

    def test_multiple_ctypes(self):

        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            @service.put(content_type=('application/json', 'text/xml'))
            def view_put(self, request):
                return self.request.validated

        swagger = CorniceSwagger([service])
        spec = swagger('IceCreamAPI', '4.2')
        self.assertEquals(spec['paths']['/icecream/{flavour}']['put']['consumes'],
                          ['application/json', 'text/xml'])

    def test_ignore_multiple_views_by_ctype(self):

        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            def view_put(self, request):
                return "red"

        service.add_view(
            "put",
            IceCream.view_put,
            validators=(colander_validator, ),
            schema=PutRequestSchema(),
            content_type='application/json',
        )
        service.add_view(
            "put",
            IceCream.view_put,
            validators=(colander_validator, ),
            schema=PutRequestSchema(),
            content_type='text/xml',
        )

        swagger = CorniceSwagger([service])
        spec = swagger('IceCreamAPI', '4.2', ignore_ctypes=['text/xml'])
        self.assertEquals(spec['paths']['/icecream/{flavour}']['put']['consumes'],
                          ['application/json'])

    def test_multiple_views_with_different_ctypes_raises_exception(self):

        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            def view_put(self, request):
                return "red"

        service.add_view(
            "put",
            IceCream.view_put,
            validators=(colander_validator, ),
            schema=PutRequestSchema(),
            content_type='application/json',
        )
        service.add_view(
            "put",
            IceCream.view_put,
            validators=(colander_validator, ),
            schema=PutRequestSchema(),
            content_type='text/xml',
        )

        swagger = CorniceSwagger([service])
        self.assertRaises(CorniceSwaggerException,
                          swagger, 'IceCreamAPI', '4.2')


class TestExtractTransformSchema(unittest.TestCase):
    def setUp(self):
        self.service = Service("IceCream", "/icecream/{flavour}")

    def test_colander_body_validator_to_full_schema(self):
        swagger = CorniceSwagger([self.service])
        service_args = dict(
            schema=BodySchema(),
            validators=(colander_body_validator,)
        )
        full_schema = swagger._extract_transform_schema(service_args)
        # ensure schema is cloned
        self.assertNotEqual(service_args['schema'], full_schema['body'])
        # ensure schema is transformed
        self.assertEqual(service_args['schema'].typ, full_schema['body'].typ)
        self.assertEqual(len(service_args['schema'].children), len(full_schema['body'].children))

    def test_schema_transform(self):
        swagger = CorniceSwagger([self.service])
        header_schema = HeaderSchema()
        service_args = dict(
            schema=GetRequestSchema()
        )

        def add_headers_transform(schema, args):
            schema['header'] = header_schema
            return schema

        swagger.schema_transformers.append(add_headers_transform)
        full_schema = swagger._extract_transform_schema(service_args)
        self.assertEqual(header_schema, full_schema['header'])
        # ensure service schema is left untouched
        self.assertNotIn('header', service_args['schema'])


class TestExtractTags(unittest.TestCase):

    def test_user_defined_tags(self):

        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            @service.get(tags=['cold', 'foo'])
            def view_get(self, request):
                return service

        swagger = CorniceSwagger([service])
        spec = swagger('IceCreamAPI', '4.2')
        validate(spec)
        tags = spec['paths']['/icecream/{flavour}']['get']['tags']
        self.assertEquals(tags, ['cold', 'foo'])

    def test_listed_default_tags(self):

        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            @service.get()
            def view_get(self, request):
                return service

        swagger = CorniceSwagger([service])
        spec = swagger('IceCreamAPI', '4.2',
                       default_tags=['cold'])
        validate(spec)
        tags = spec['paths']['/icecream/{flavour}']['get']['tags']
        self.assertEquals(tags, ['cold'])

    def test_callable_default_tags(self):

        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            @service.get()
            def view_get(self, request):
                return service

        def default_tag_callable(service):
            return ['cold']

        swagger = CorniceSwagger([service])
        spec = swagger('IceCreamAPI', '4.2',
                       default_tags=default_tag_callable)
        validate(spec)
        tags = spec['paths']['/icecream/{flavour}']['get']['tags']
        self.assertEquals(tags, ['cold'])

    def test_invalid_tag_raises_exception(self):

        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            @service.get(tags='cold')
            def view_get(self, request):
                return service

        swagger = CorniceSwagger([service])
        self.assertRaises(CorniceSwaggerException,
                          swagger, 'IceCreamAPI', '4.2')


class NotInstantiatedSchemaTest(unittest.TestCase):

    def test_not_instantiated(self):
        service = Service("IceCream", "/icecream/{flavour}")

        class IceCream(object):
            """
            Ice cream service
            """

            # Use GetRequestSchema and ResponseSchemas classes instead of objects
            @service.get(validators=(colander_validator, ),
                         schema=GetRequestSchema)
            def view_get(self, request):
                """Serve icecream"""
                return self.request.validated

            @service.put(validators=(colander_validator, ), schema=PutRequestSchema())
            def view_put(self, request):
                """Add flavour"""
                return self.request.validated

        self.service = service
        self.swagger = CorniceSwagger([self.service])
        self.spec = self.swagger('IceCreamAPI', '4.2')
        validate(self.spec)
