import os
import sys
import logging
import simplejson
from sugar.activity import activity
import zipfile


class GameModel:

    def __init__(self):
        self.data = {}
        self.data['questions'] = []
        """
        question = {'question' = '',
                    'type' = ''  # TEXT / GRAPH
                    'replies' [ {'text': '',
                                'valid': } # True / False
                    'file_graph_display' = '',
                    'file_graph_mask' = ''}
        """

        self.data['resources'] = []
        """
        resource = {'title' = '',
                    'file_image' = ''
                    'file_text' = ''}
        """

        self.data['map_data'] = None

    def write(self, file_name):

        instance_path = os.path.join(activity.get_activity_root(), 'instance')

        data_file_name = 'data.json'
        f = open(os.path.join(instance_path, data_file_name), 'w')
        try:
            simplejson.dump(self.data, f)
        finally:
            f.close()

        logging.error('write file_name %s', file_name)

        z = zipfile.ZipFile(file_name, 'w')
        z.write(os.path.join(instance_path, data_file_name).encode('ascii',
            'ignore'), data_file_name.encode('ascii', 'ignore'))

        for resource in self.data['resources']:
            z.write(resource['file_image'], os.path.join('resources',
                    os.path.basename(resource['file_image'])))
            z.write(resource['file_text'], os.path.join('resources',
                    os.path.basename(resource['file_text'])))

        z.close()

    def read(self, file_name):

        logging.error('model.read %s', file_name)
        instance_path = os.path.join(activity.get_activity_root(), 'instance')
        z = zipfile.ZipFile(file_name, 'r')
        self.check_resources_directory()
        for zipped_file in z.namelist():
            if (zipped_file != './'):
                try:
                    logging.error('extrayendo %s', zipped_file)
                    # la version de python en las xo no permite hacer
                    # extract :(
                    # z.extract(file_name,instance_path)
                    data = z.read(zipped_file)
                    fout = open(os.path.join(instance_path, zipped_file), 'w')
                    fout.write(data)
                    fout.close()
                except:
                    logging.error('Error extrayendo %s', zipped_file)
        z.close()
        data_file_name = 'data.json'

        f = open(os.path.join(instance_path, data_file_name), 'r')
        try:
            self.data = simplejson.load(f)

            if not 'resources' in self.data:
                self.data['resources'] = []

        finally:
            f.close()

    def check_resources_directory(self):
        resource_path = os.path.join(activity.get_activity_root(),
                'instance', 'resources')
        if not os.path.exists(resource_path):
            os.makedirs(resource_path)
