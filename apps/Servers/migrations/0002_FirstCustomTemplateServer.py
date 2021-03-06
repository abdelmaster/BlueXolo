# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-10-12 20:17
from __future__ import unicode_literals

from django.db import migrations


def first_template_server(apps, schema_editor):
    TemplateServer = apps.get_model('Servers', 'TemplateServer')

    TemplateServer.objects.get_or_create(
        name="SSH Connection",
        description="",
        parameters="[{\"parameter\":\"host\",\"help_text\":\"\",\"category\":\"1\",\"value_type\":\"1\"},{\"parameter\":\"user\",\"help_text\":\"\",\"category\":\"1\",\"value_type\":\"1\"},{\"parameter\":\"passwd\",\"help_text\":\"\",\"category\":\"1\",\"value_type\":\"1\"},{\"parameter\":\"${var_to_test}\",\"help_text\":\"\",\"category\":\"2\",\"value_type\":\"1\"},{\"parameter\":\"${cline}\",\"help_text\":\"\",\"category\":\"2\",\"value_type\":\"1\"},{\"parameter\":\"${text_to_append}\",\"help_text\":\"\",\"category\":\"2\",\"value_type\":\"1\"},{\"parameter\":\"${Mandatory}\",\"help_text\":\"\",\"category\":\"2\",\"value_type\":\"1\"},{\"parameter\":\"path\",\"help_text\":\"\",\"category\":\"1\",\"value_type\":\"1\"}]"
    )
    print('\n  --------------------------------------- Server Template :D  --------------------------')


def reverse_func(apps, schema_editor):
    TemplateServer = apps.get_model("Servers", "TemplateServer")
    db_alias = schema_editor.connection.alias
    TemplateServer.objects.using(db_alias).all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('Servers', '0001_initial'),
    ]

    operations = [
        
    ]
