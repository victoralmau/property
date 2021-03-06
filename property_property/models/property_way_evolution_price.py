# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging
from odoo import api, fields, models
import requests
import json
from datetime import datetime
import time
_logger = logging.getLogger(__name__)


class PropertyWayEvolutionPrice(models.Model):
    _name = 'property.way.evolution.price'
    _description = 'Property Way Evolution Price'

    property_way_id = fields.Many2one(
        comodel_name='property.way',
        string='Property Way Id'
    )
    property_home_type_id = fields.Many2one(
        comodel_name='property.home.type',
        string='Property Home Type Id'
    )
    property_transaction_type_id = fields.Many2one(
        comodel_name='property.transaction.type',
        string='Property Transaction Type Id'
    )
    radius = fields.Integer(
        string='Surface Area'
    )
    full = fields.Boolean(
        string='Full'
    )
    date_last_check = fields.Date(
        string='Date Last Check'
    )
    source = fields.Selection(
        selection=[
            ('bbva', 'BBVA')
        ],
        string='Source2',
        default='bbva'
    )

    @api.multi
    def bbva_generate_tsec(self):
        self.ensure_one()
        tsec = False
        url = 'https://www.bbva.es/ASO/TechArchitecture/grantingTicketsOauth/V01/'
        key = self.env['ir.config_parameter'].sudo().get_param('bbva_authorization_key')
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': 'Basic %s' % key
        }
        data_obj = {
            'grant_type': 'client_credentials'
        }
        response = requests.post(url, headers=headers, data=data_obj)
        if response.status_code == 200:
            response_json = json.loads(response.text)
            if 'access_token' in response_json:
                tsec = str(response_json['access_token'])

        return tsec

    @api.multi
    def action_check(self, tsec):
        self.ensure_one()
        current_date = datetime.now()
        model_p_w_e_p_d = 'property.way.evolution.price.detail'
        key_p_w_e_p_id = 'property_way_evolution_price_id'
        # return
        return_item = {
            'errors': False,
            'status_code': 200,
            'error': ''
        }
        # requests
        url = 'https://%s/ASO/financialPropertyInformation/V01/%s/' % (
            'www.bbva.es',
            'getEvolutionPriceReport'
        )
        body_obj = {
            "location": {
                "latitude": str(self.property_way_id.latitude),
                "longitude": str(self.property_way_id.longitude)
            },
            "homeType": {
                "id": str(self.property_home_type_id.external_id)
            },
            "transactionType": {
                "id": str(self.property_transaction_type_id.external_id)
            },
            "monthsQuantity": 36,
            "monthsBetweenStreches": 1,
            "radius": self.radius
        }
        headers = {
            'content-type': 'application/json',
            'tsec': str(tsec)
        }
        _logger.info(self.property_way_id.id)
        response = requests.post(url, headers=headers, data=json.dumps(body_obj))
        if response.status_code == 200:
            response_json = json.loads(response.text)
            if 'report' in response_json:
                if len(response_json['report']) > 0:
                    for report_item in response_json['report']:
                        if 'year' not in report_item:
                            continue

                        if 'month' not in report_item:
                            continue

                        price_detail_ids = self.env[model_p_w_e_p_d].search(
                            [
                                (key_p_w_e_p_id, '=', self.id),
                                ('month', '=', int(report_item['month'])),
                                ('year', '=', int(report_item['year']))
                            ]
                        )
                        if len(price_detail_ids) == 0:
                            # vals
                            vals = {
                                key_p_w_e_p_id: self.id,
                                'month': int(report_item['month']),
                                'year': int(report_item['year']),
                            }
                            # homesSold
                            if 'homesSold' in report_item:
                                vals['homes_sold'] = int(report_item['homesSold'])
                            # averageSurfaceArea
                            if 'averageSurfaceArea' in report_item:
                                averageSA = report_item['averageSurfaceArea']
                                vals['average_surface_area'] = averageSA
                            # averagePriceBySquareMeter
                            if 'averagePriceBySquareMeter' in report_item:
                                averagePBSM = report_item['averagePriceBySquareMeter']
                                if 'amount' in averagePBSM:
                                    vals[
                                        'average_price_by_sqare_meter'
                                    ] = averagePBSM['amount']
                            # averagePrice
                            if 'averagePrice' in report_item:
                                averagePrice = report_item['averagePrice']
                                if 'amount' in averagePrice:
                                    vals['average_price'] = averagePrice['amount']
                            # create
                            self.env[model_p_w_e_p_d].sudo().create(vals)
        # update date_last_check + total_build_units
        self.date_last_check = current_date.strftime("%Y-%m-%d")
        # return
        return return_item

    @api.model
    def cron_check_ways_evolution_price(self):
        # def
        model_p_w_e_p = 'property.way.evolution.price'
        key_p_t_t_id = 'property_transaction_type_id'
        # search
        home_type_ids = self.env['property.home.type'].search(
            [
                ('id', '>', 0)
            ]
        )
        transaction_type_ids = self.env['property.transaction.type'].search(
            [
                ('id', '>', 0)
            ]
        )
        # first_create property.way.evolution.price
        if home_type_ids:
            for home_type_id in home_type_ids:
                if transaction_type_ids:
                    for transaction_type_id in transaction_type_ids:
                        evolution_price_ids = self.env[model_p_w_e_p].search(
                            [
                                ('property_home_type_id', '=', home_type_id.id),
                                (key_p_t_t_id, '=', transaction_type_id.id)
                            ]
                        )
                        if evolution_price_ids:
                            way_ids = self.env['property.way'].search(
                                [
                                    (
                                        'id',
                                        'not in',
                                        evolution_price_ids.mapped(
                                            'property_way_id'
                                        ).ids
                                    ),
                                    ('latitude', '!=', False),
                                    ('longitude', '!=', False)
                                ]
                            )
                        else:
                            way_ids = self.env['property.way'].search(
                                [
                                    ('latitude', '!=', False),
                                    ('longitude', '!=', False)
                                ]
                            )
                        # operations-generate
                        if way_ids:
                            for way_id in way_ids:
                                vals = {
                                    'property_way_id': way_id.id,
                                    'property_home_type_id': home_type_id.id,
                                    key_p_t_t_id: transaction_type_id.id,
                                    'radius': 500,
                                    'source': 'bbva'
                                }
                                self.env[model_p_w_e_p].sudo().create(vals)
        # now check all property.way.evolution.price
        evolution_price_ids = self.env[model_p_w_e_p].search(
            [
                ('full', '=', False)
            ],
            limit=2000
        )
        if evolution_price_ids:
            count = 0
            # generate_tsec
            tsec = self.bbva_generate_tsec()
            if tsec:
                for evolution_price_id in evolution_price_ids:
                    count += 1
                    # action_check
                    return_item = evolution_price_id.action_check(tsec)[0]
                    if 'errors' in return_item:
                        if return_item['errors']:
                            _logger.info(return_item)
                            # fix
                            if return_item['status_code'] != 403:
                                break
                            else:
                                _logger.info('Raro que sea un 403 pero pasamos')
                                tsec = self.bbva_generate_tsec()
                    # _logger
                    percent = (float(count)/float(len(evolution_price_ids)))*100
                    percent = "{0:.2f}".format(percent)
                    _logger.info('%s - %s%s (%s/%s)' % (
                        evolution_price_id.id,
                        percent,
                        '%',
                        count,
                        len(evolution_price_ids)
                    ))
                    # update
                    if return_item['status_code'] != 403:
                        evolution_price_id.full = True
                    # Sleep 1 second to prevent error (if request)
                    time.sleep(1)
