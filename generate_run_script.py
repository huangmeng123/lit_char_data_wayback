import argparse
import configparser
import os, stat

def get_args():
    parser = argparse.ArgumentParser(
        description='Configurate data generating process'
    )
    parser.add_argument(
        '-o', '--output', type=str, dest='output_filename',
        help='the output file path',
    )
    parser.add_argument(
        '-i', '--dbname', type=str, dest='dbname',
        help='the name of the input database',
    )
    parser.add_argument(
        '--host', type=str, default='localhost',
        help='the host of the input database',
    )
    parser.add_argument(
        '--user', type=str, help='a user that can access the input database',
    )
    parser.add_argument(
        '--password', type=str, help='the password of the database user',
    )
    return parser.parse_args()

def main():
    args = get_args()
    config = configparser.ConfigParser()
    config['database'] = {
        'host': args.host,
        'user': args.user,
        'password': args.password,
        'dbname': args.dbname,
    }
    config['output'] = {
        'filename': args.output_filename,
        'train_filename': 'train_' + args.output_filename,
        'test_filename': 'test_' + args.output_filename,
        'val_filename': 'val_' + args.output_filename,
    }
    with open('runtime.ini', 'w') as config_f:
        config.write(config_f)

    with open('run.sh', 'w') as script_f:
        script_f.write(
            f'export PGPASSWORD=\'{args.password}\'\n'
            f'createdb -U {args.user} -h {args.host} {args.dbname}\n'
            f'psql -U {args.user} -h {args.host} {args.dbname} '
            f'-f database/create_tables.sql\n'
            'cd scraper\n'
            'scrapy crawl wayback_lit\n'
            'scrapy crawl wayback_char\n'
            'cd ..\n'
            'python main.py'
        )
    
    st = os.stat('run.sh')
    os.chmod('run.sh', st.st_mode | stat.S_IEXEC)

if __name__ == '__main__':
    main()