# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import asyncio
import json
import logging
import lzma
import os
from datetime import datetime
from typing import List

import aiohttp
import click

IMPORTED_DATA_DIR = os.path.join(os.path.dirname(__file__), 'imported-data')
TMP_FILE = os.path.join(IMPORTED_DATA_DIR, '_mailchimp_tmp_data.xz')

logger = logging.getLogger()


async def get_last_imported_data() -> List[dict]:
    os.makedirs(IMPORTED_DATA_DIR, exist_ok=True)
    last_imported_file = None
    for _, _, files in os.walk(IMPORTED_DATA_DIR):
        for file in reversed(sorted(f for f in files if f.endswith('jsonl.xz'))):
            last_imported_file = os.path.join(IMPORTED_DATA_DIR, file)
            break
        break
    if not last_imported_file:
        logger.info(f'There is no previous run data')
        return []
    data = []
    with lzma.open(last_imported_file, mode='rt') as file:
        for line in file.readlines():
            data.append(json.loads(line))
    return data


async def get_mailchimp_data(mailchimp_api_key, mailchimp_list_id):
    mailchimp_data = []
    async with aiohttp.ClientSession(headers={'Authorization': f'apikey {mailchimp_api_key}'},
                                     connector=aiohttp.TCPConnector(limit=9)) as session:
        async def get_page(page):
            async with session.get(f'https://us9.api.mailchimp.com/3.0/lists/{mailchimp_list_id}/members?count=100&'
                                   f'offset={page*100}') as res:
                if res.status >= 400:
                    logger.error(f'There is something wrong with the requests to mailchimp')
                    logger.warning(f'{res.status} {res.reason}')
                    data = await res.text()
                    logger.warning(f'Response give: {data}')
                    raise RuntimeError('Mailchimp did not let us through')
                page_members = await res.json()
                mailchimp_data.extend(page_members['members'])

                return page_members['total_items']

        total_items = await get_page(0)
        total_pages = int((total_items / 100) + 1)

        pages = []
        for page in range(1, total_pages):
            pages.append(get_page(page))

        await asyncio.gather(*pages)

    with lzma.open(TMP_FILE, mode='wt') as fd:
        fd.writelines(f'{json.dumps(member)}\n' for member in mailchimp_data)

    return mailchimp_data


def diff_imported_data(old_data, new_data):
    # TODO: The spec says we should get the name and surname from somewhere, but I cannot find it
    old_members = {(member['id'], member['email_address']) for member in old_data}
    new_members = {(member['id'], member['email_address']) for member in new_data}

    to_add_set = new_members - old_members
    to_remove_set = old_members - new_members

    to_add_members, to_remove_members = [], []
    for member in to_add_set:
        to_add_members.append({'id': member[0], 'email': member[1]})
    for member in to_remove_set:
        to_remove_members.append({'id': member[0], 'email': member[1]})

    return to_add_members, to_remove_members


async def async_main(mailchimp_api_key, mailchimp_list_id, ometria_endpoint, ometria_api_key):
    logger.info('Starting sync program execution')
    last_data = await get_last_imported_data()
    logger.debug(f'Got {len(last_data)} entries from the last import')
    new_data = await get_mailchimp_data(mailchimp_api_key, mailchimp_list_id)
    logger.debug(f'Got {len(new_data)} entries from mailchimp')
    # TODO: There is no documentation on how to execute removals
    additions, removals = diff_imported_data(last_data, new_data)
    logger.debug(f'{len(additions)} additions and {len(removals)} to be done.')

    async with aiohttp.ClientSession(headers={'Authorization': f'{ometria_api_key}'}) as session:
        if additions:
            async with session.post(ometria_endpoint, json=additions) as resp:
                if resp.status >= 400:
                    logger.error(f'Failed to submit {len(additions)} to the API')
                    logger.warning(f'{resp.status} {resp.reason}')
                    data = await resp.text()
                    logger.warning(f'Response give: {data}')
                    raise ValueError(f'Failed to submit data to Ometria API')
                logger.info(f'{len(additions)} Additions to the API where submitted successfully')

        # TODO: Here would go the removal

    os.link(TMP_FILE, os.path.join(IMPORTED_DATA_DIR, datetime.utcnow().strftime('%Y%m%dT%H%M%S.jsonl.xz')))
    os.remove(TMP_FILE)


@click.command()
@click.option('--mailchimp-api-key', '-m', default=lambda: os.environ['MAILCHIMP_API_KEY'])
@click.option('--mailchimp-list-id', '-l', default=lambda: os.environ['MAILCHIMP_LIST_ID'])
@click.option('--ometria-endpoint', '-o', default=lambda: os.environ['OMETRIA_ENDPOINT'])
@click.option('--ometria-api-key', '-a', default=lambda: os.environ['OMETRIA_API_KEY'])
@click.option('--verbose', '-v', count=True)
def main(mailchimp_api_key, mailchimp_list_id, ometria_endpoint, ometria_api_key, verbose):
    levels = [logging.WARNING, logging.INFO, logging.DEBUG]

    logging.basicConfig(
        level=levels[min(2, verbose)],
        datefmt="%Y%m%dT%H%M%S",
        format='%(asctime)s:%(name)s:%(levelname)s - %(message)s'
    )

    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_main(mailchimp_api_key, mailchimp_list_id, ometria_endpoint, ometria_api_key))


if __name__ == '__main__':
    main()
