from typing import Optional
from tortoise import fields, models
from pydantic import BaseModel

class Users(models.Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=20, unique=True)
    full_name = fields.CharField(max_length=50, null=True)
    password = fields.CharField(max_length=128, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    modified_at = fields.DatetimeField(auto_now=True)

class Transactions(models.Model):
    id = fields.IntField(pk=True)
    action = fields.CharField(max_length=20)
    bucket_name = fields.TextField()
    file_path = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)
    modified_at = fields.DatetimeField(auto_now=True)

class Vector(models.Model):
    id = fields.IntField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    modified_at = fields.DatetimeField(auto_now=True)
    file_name = fields.CharField(max_length=100, null=True)
    file = fields.CharField(max_length=255, null=True, blank=True)

class Raster(models.Model):
    id = fields.IntField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    modified_at = fields.DatetimeField(auto_now=True)
    file_name = fields.CharField(max_length=100, null=True)
    file = fields.CharField(max_length=255, null=True, blank=True)

class Boundary(models.Model):
    id = fields.IntField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    modified_at = fields.DatetimeField(auto_now=True)
    file_name = fields.CharField(max_length=100, null=True)
    file = fields.CharField(max_length=255, null=True, blank=True)

class Overlay(models.Model):
    id = fields.IntField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    modified_at = fields.DatetimeField(auto_now=True)
    file_name = fields.CharField(max_length=100, null=True)
    file = fields.CharField(max_length=255, null=True, blank=True)

    