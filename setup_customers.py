#!/usr/bin/env python3

from db_utils import *

# Create customers table and add sample data
try:
    # Check if table exists first
    tables = get_custom_tables()
    table_exists = any(table['table_name'] == 'customers' for table in tables)
    
    if not table_exists:
        result = create_custom_table('customers', [
            {'name': 'name', 'type': 'string', 'required': False, 'unique': False},
            {'name': 'number', 'type': 'string', 'required': False, 'unique': False}
        ], 'Customer names and numbers')
        
        if result[0]:  # Success
            print('Created customers table successfully')
        else:
            print(f'Error creating table: {result[1]}')
            exit(1)
    else:
        print('Customers table already exists')
        
    # Add sample data
    sample_customers = [
        {'name': 'Acme Corporation', 'number': 'ACME001'},
        {'name': 'TechSoft Solutions', 'number': 'TECH002'}, 
        {'name': 'Global Industries', 'number': 'GLOB003'},
        {'name': 'Smith & Associates', 'number': 'SMTH004'},
        {'name': 'Future Systems Inc', 'number': 'FUTR005'}
    ]
    
    added_count = 0
    for customer in sample_customers:
        success, error = insert_custom_table_row('customers', customer)
        if success:
            name = customer['name']
            number = customer['number']
            print(f'Added customer: {name} - {number}')
            added_count += 1
        else:
            if 'UNIQUE constraint failed' in str(error):
                print(f'Customer already exists: {customer["name"]}')
            else:
                print(f'Error adding customer: {error}')
    
    print(f'Added {added_count} new customers')
            
except Exception as e:
    print(f'Error: {e}')
