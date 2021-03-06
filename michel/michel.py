#!env python
"""
Pushes/pulls flat text files to google tasks

USAGE:
    michel pull                 prints the default tasklist on stdout
    michel push <textfile>      replace the default tasklist with the
                                content of <textfile>.
"""
from __future__ import with_statement
import gflags
import httplib2
from apiclient.discovery import build
from oauth2client.file import Storage
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.tools import run
from xdg.BaseDirectory import save_config_path, save_data_path
import os.path
import sys
import re
#import pprint

def get_service():
    """
    Handle oauth's shit (copy-pasta from
    http://code.google.com/apis/tasks/v1/using.html)
    Yes I do publish a secret key here, apparently it is normal
    http://stackoverflow.com/questions/7274554/why-google-native-oauth2-flow-require-client-secret
    """
    FLAGS = gflags.FLAGS
    FLOW = OAuth2WebServerFlow(
            client_id='617841371351.apps.googleusercontent.com',
            client_secret='_HVmphe0rqwxqSR8523M6g_g',
            scope='https://www.googleapis.com/auth/tasks',
            user_agent='michel/0.0.1')
    FLAGS.auth_local_webserver = False
    storage = Storage(os.path.join(save_data_path("michel"), "oauth.dat"))
    credentials = storage.get()
    if credentials is None or credentials.invalid == True:
        credentials = run(FLOW, storage)
    http = httplib2.Http()
    http = credentials.authorize(http)
    return build(serviceName='tasks', version='v1', http=http)

def print_todolist():
    service = get_service()
    tasks = service.tasks().list(tasklist='@default').execute()
    levels = {}
    #pprint.pprint(tasks)
    for task in tasks.get('items', []):
	if task['status'] == 'completed':
	    continue
        parent_id = task.get('parent')
        if parent_id:
            level = levels[parent_id] + 1
        else:
            level = 0
        levels[task['id']] = level
        title   = task['title'].encode('utf-8')
	duedate = "\t!"+task['due'] if 'due' in task is not None else  ""
        print('\t'.join(['' for i in range(level + 1)]) + title + duedate)

def wipe_todolist():
    service = get_service()
    tasks = service.tasks().list(tasklist='@default').execute()
    for task in tasks.get('items', []):
        service.tasks().delete(tasklist='@default',
                task=task['id']).execute()

def push_todolist(path):
    wipe_todolist()
    service = get_service()
    with open(path) as f:
        last_inserted = None
        last_inserted_at_level = {}
        for line in f:
            if line[-1] == '\n':
                line = line[:-1]
            level = 0
            while line[0] == '\t':
                line = line[1:]
                level += 1

	    """
	    " pretty sure we want to and duedate if line ends with \t!####-##-##...
	    " time in form 2011-11-10T00:00:00.000Z
	    " what is Z?
	    " 400 error if date doesn't have .000Z
	    "TODO:
	    " could probably search for !####-##-##...
	    " set match to duedate
	    " remove match from title string
	    """
	    # what's the elgant python way to assign a split string?

	    task=line.split("\t!")
	    if len(task) == 1 or not re.match('^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}Z',task[-1]):
		title= line
		duedate= None
	    else:
		#just incase there were a bunch of \t! through the task title
		#only take the last one, join back the rest
		(title, duedate) = ('\t!'.join(task[:-1]),task[-1])

            args = {'tasklist':'@default', 'body':{ 'title' : title } }
	    if duedate is not None:
		args['body']['due']=duedate
            if level:
                args['parent'] = last_inserted_at_level[level - 1]
            if args.get('parent') != last_inserted:
                args['previous'] = last_inserted_at_level[level]
            result = service.tasks().insert(**args).execute()
            last_inserted = result['id']
            last_inserted_at_level[level] = result['id']

def main():
    if (len(sys.argv)) < 2:
        print(__doc__)
    elif sys.argv[1] == "pull":
        print_todolist()
    elif sys.argv[1] == "push":
        if not len(sys.argv) == 3:
            print("'push' expects exactly 1 argument")
            sys.exit(2)
        path = sys.argv[2]
        if not os.path.exists(path):
            print("The file you want to push does not exist.")
            sys.exit(2)
        push_todolist(path)
    else:
        print(__doc__)
        sys.exit(2)

if __name__ == "__main__":
    main()
