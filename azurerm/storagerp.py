#!/usr/bin/env python

"""
Copyright (c) 2016, Guy Bowerman
Description: Azure Resource Manager Python library
License: MIT (see LICENSE file for details)
"""

# storagerp.py - azurerm functions for the Microsoft.Storage resource provider

from .settings import azure_rm_endpoint, STORAGEAPI
from .restfns import do_delete, do_get, do_put, do_post

# create_storage_account(access_token, subscription_id, rgname, account_name, location)
# create a storage account in the specified location and resource group
# Note: just standard storage for now. Could add a storageType argument later.
def create_storage_account(access_token, subscription_id, rgname, account_name, location):
    endpoint = ''.join([azure_rm_endpoint,
						'/subscriptions/', subscription_id,
						'/resourcegroups/', rgname,
						'/providers/Microsoft.Storage/storageAccounts/', account_name,
						'?api-version=', STORAGEAPI])
    body = ''.join(['{\n   "location": "', location, '",\n',
					'   "properties": {\n      "accountType": "Standard_LRS"\n   }\n}'])
    return do_put(endpoint, body, access_token)

# delete_storage_account(access_token, subscription_id, rgname, account_name)
# delete a storage account in the specified resource group
def delete_storage_account(access_token, subscription_id, rgname, account_name):
    endpoint = ''.join([azure_rm_endpoint,
						'/subscriptions/', subscription_id,
						'/resourcegroups/', rgname,
						'/providers/Microsoft.Storage/storageAccounts/', account_name,
						'?api-version=', STORAGEAPI])
    return do_delete(endpoint, access_token)

# get_storage_account(access_token, subscription_id, rgname, account_name)
# get the properties for the named storage account
def get_storage_account(access_token, subscription_id, rgname, account_name):
    endpoint = ''.join([azure_rm_endpoint,
						'/subscriptions/', subscription_id,
						'/resourcegroups/', rgname,
						'/providers/Microsoft.Storage/storageAccounts/', account_name,
						'?api-version=', STORAGEAPI])
    return do_get(endpoint, access_token)

# list_storage_accounts_rg(access_token, subscription_id, rgname)
# list the storage accounts in the specified resource group
def list_storage_accounts_rg(access_token, subscription_id, rgname):
    endpoint = ''.join([azure_rm_endpoint,
						'/subscriptions/', subscription_id,
						'/resourcegroups/', rgname,
						'/providers/Microsoft.Storage/storageAccounts',
						'?api-version=', STORAGEAPI])
    return do_get(endpoint, access_token)

# list_storage_accounts_sub(access_token, subscription_id)
# list the storage accounts in the specified subscription
def list_storage_accounts_sub(access_token, subscription_id):
    endpoint = ''.join([azure_rm_endpoint,
						'/subscriptions/', subscription_id,
						'/providers/Microsoft.Storage/storageAccounts',
						'?api-version=', STORAGEAPI])
    return do_get(endpoint, access_token)

# get_storage_account_keys(access_token, subscription_id, rgname, account_name)
# get the access keys for the specified storage account
def get_storage_account_keys(access_token, subscription_id, rgname, account_name):
    endpoint = ''.join([azure_rm_endpoint,
						'/subscriptions/', subscription_id,
						'/resourcegroups/', rgname,
						'/providers/Microsoft.Storage/storageAccounts/', account_name,
						'/listKeys',
						'?api-version=', STORAGEAPI])
    return do_post(endpoint, '', access_token)

# get_storage_usage(access_token, subscription_id)
# returns storage usage and quota information for the specified subscription
def get_storage_usage(access_token, subscription_id):
    endpoint = ''.join([azure_rm_endpoint,
						'/subscriptions/', subscription_id,
						'/providers/Microsoft.Storage/usages',
						'?api-version=', STORAGEAPI])
    return do_get(endpoint, access_token)