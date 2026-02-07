from django.test import TestCase, Client


class CategoriesOrderingTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_categories_ordering_and_names(self):
        resp = self.client.get('/api/categories/', HTTP_ACCEPT='application/json')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        results = data.get('results', [])
        self.assertGreaterEqual(len(results), 3)
        self.assertEqual(results[0]['name'], 'Cocktails Throughout History')
        self.assertEqual(results[1]['name'], 'Shots')
        self.assertEqual(results[2]['name'], 'My Recipes')
