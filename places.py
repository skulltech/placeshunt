import csv

import requests
import yaml

with open('data.yaml') as f:
    data = yaml.load(f)
with open('secrets.yaml') as f:
    secrets = yaml.load(f)
APIKey = secrets['Google']['APIKey']


def update_cache(zip, code):
    data['geocode'][zip] = code
    with open('data.yaml', 'w') as f:
        yaml.dump(data, f)


class GMaps:
    def __init__(self, key=None):
        self.key = key

    def geocode(self, zip):
        if zip in data['geocode']:
            return data['geocode'][zip]
        endpoint = 'https://maps.googleapis.com/maps/api/geocode/json'
        params = {'components': f'country:US|postal_code:{zip}', 'key': self.key}
        response = requests.get(endpoint, params=params).json()
        if 'ZERO_RESULTS' in response['status']:
            print(f'Invalid zipcode: {zip}')
            update_cache(zip, False)
            return False
        code = response['results'][0]['geometry']
        update_cache(zip, code)
        return code

    def places(self, query, zip):
        if isinstance(zip, list):
            ids = []
            for i in zip:
                print(f'[*] Searching for places in zipcode: {i}')
                ids = ids + self.search(query, i)
            ids = list(set(ids))
        else:
            ids = self.search(query, zip)
        return [self.details(place) for place in ids]

    def search(self, query, zip):
        geo = self.geocode(zip)
        if not geo:
            return []
        rectangle = geo.get('bounds') or geo['viewport']
        params = {
            'key': self.key,
            'input': query,
            'inputtype': 'textquery',
            'locationbias': f'rectangle:{rectangle["southwest"]["lat"]},{rectangle["southwest"]["lng"]}|{rectangle["northeast"]["lat"]},{rectangle["northeast"]["lng"]}'
        }
        endpoint = 'https://maps.googleapis.com/maps/api/place/findplacefromtext/json'
        response = requests.get(endpoint, params=params)
        return [place['place_id'] for place in response.json()['candidates']]

    def details(self, place_id):
        endpoint = 'https://maps.googleapis.com/maps/api/place/details/json'
        params = {
            'key': self.key,
            'place_id': place_id,
            'fields': ','.join(['name', 'address_components', 'formatted_address', 'formatted_phone_number', 'url'])
        }
        response = requests.get(endpoint, params=params)
        place = response.json()['result']
        for component in place['address_components']:
            if 'locality' in component['types']:
                place['city'] = component['long_name']
            elif 'postal_code' in component['types']:
                place['zip'] = component['long_name']
            elif 'administrative_area_level_1' in component['types']:
                place['state'] = component['long_name']
        return place


def main():
    file = input('[*] Name of the file containing zip codes [default: zips.csv]: ') or 'zips.csv'
    query = input('[*] The search query: ')
    maps = GMaps(APIKey)
    with open(file) as f:
        zips = f.read().splitlines()
    with open(f'output-{query}.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['name', 'city', 'state', 'zipcode', 'address', 'phone', 'URL'])
        output = maps.places(query, zips)
        output = [
            [o['name'], o['city'], o['state'], o['zip'], o['formatted_address'], o['formatted_phone_number'], o['url']]
            for o in output]
        for row in output:
            writer.writerow(row)
    print('[*] Completed!')


if __name__ == '__main__':
    main()
