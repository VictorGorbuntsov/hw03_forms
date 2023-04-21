from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django import forms

from posts.models import Post, Group

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='HasNoName')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовый текст'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Собираем в словарь пары "имя_html_шаблона: reverse(name)"
        templates_pages_names = {
            'posts/index.html': reverse('posts:home'),
            'posts/create_post.html': reverse('posts:create_post'),
            'posts/group_list.html': reverse('posts:group_list'),
            'posts/post_detail.html': (
                reverse('posts:post_detail', kwargs={'slug': 'test-slug'})
            ),
        }
        for template, reverse_name in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_context(self):
        """Шаблон Index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        post = Post.objects.select_related('author').all()[0]
        page_obj = response.context['page_obj'][0]
        self.assertIn('page_obj', response.context)
        self.assertEqual(page_obj, post)

    def test_group_list_context(self):
        """Проверка Group list использует правильные данные в контекст."""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug_name': 'test_slug'}))
        post = Post.objects.select_related(
            'author', 'group').filter(group=self.group)[0]

        page_obj = response.context['page_obj'][0]

        self.assertIn('page_obj', response.context)
        self.assertIn('group', response.context)
        self.assertEqual(page_obj, post)

    def test_profile_context(self):
        """Проверка profile использует правильный контекст."""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': 'NoName'}))
        post = Post.objects.select_related(
            'author', 'group').filter(author=self.user)[0]
        page_obj = response.context['page_obj'][0]

        self.assertIn('page_obj', response.context)
        self.assertIn('author', response.context)
        self.assertEqual(page_obj, post)

    def test_post_detail_context(self):
        """Проверка Post detail использует правильный контекст."""
        response = self.authorized_client.get(reverse(
            'posts:post_detail', kwargs={'post_id': self.post.id}))

        post = response.context['post']

        self.assertEqual(post, self.post)

    def test_post_create_context(self):
        """Post create page и post_create использует правильный контекст."""
        response = self.authorized_client.get(reverse('posts:post_create'))

        form_fields = {'text': forms.fields.CharField,
                       'group': forms.fields.ChoiceField}

        self.assertIn('is_edit', response.context)
        self.assertFalse(response.context['is_edit'])

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_context(self):
        """Post create page with post_edit использует правильный контекст."""
        response = self.authorized_client.get(reverse(
            'posts:post_edit', kwargs={'post_id': self.post.id}))

        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }

        form_field_text = response.context.get('form')['text'].value()
        form_field_group = response.context.get('form')['group'].value()

        self.assertEqual(form_field_text, self.post.text)
        self.assertEqual(form_field_group, self.post.group.pk)
        self.assertIn('is_edit', response.context)
        self.assertTrue(response.context['is_edit'])

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)


class PaginatorViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create(username='NoName')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )

        for page in range(10):
            Post.objects.create(
                text=f'Test text №{page}',
                author=cls.user,
                group=cls.group,
            )

    def test_paginator_first_page(self):
        """Проверка корректной работы paginator."""
        list_of_check_page = ['/', '/group/test_slug/', '/profile/NoName/']
        for page in list_of_check_page:
            with self.subTest(adress=page):
                response = self.client.get(page)
                self.assertEqual(
                    len(response.context['page_obj']), 15)
                response = self.client.get(page + '?page=2')
                self.assertEqual(
                    len(response.context['page_obj']),
                    10 - 15)
