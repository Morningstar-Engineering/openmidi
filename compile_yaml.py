import yaml
import os
import json

if __name__ == '__main__':

    file_path = 'data/mapping.json'
    mapping_data = json.loads(open(file_path).read())

    data = {}

    for i in mapping_data['brands']:
        brand_name = i['name']
        brand_name_value = i['value']
        models = i['models']
        for j in models:
            model_name = j['name']
            model_value = j['value']
            model_file_path = 'data/brands/{brand}/{model}.yaml'.format(
                brand=brand_name_value,
                model=model_value
            )

            if brand_name_value not in data.keys():
                data[brand_name_value] = {}
            print(brand_name)
            print(model_name)
            print("Adding %s :: %s" % (brand_name, model_name))
            data[brand_name_value][model_value] = yaml.safe_load(open(model_file_path, 'r').read())


    file_path_to_write = 'data/all.json'

    if os.path.isfile(file_path_to_write):
        print("Deleting %s" % file_path_to_write)
        os.remove(file_path_to_write)

    with open(file_path_to_write, 'w') as outfile:
        json.dump(data, outfile)