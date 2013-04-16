# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution - module extension
#    Copyright (C) 2011- O4SB (<http://openforsmallbusiness.co.nz>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
'''bom_variant_multi Openerp Module'''

from osv import osv
from osv import fields
from tools.translate import _
import tools

def rounding(factor, round_):
    '''Simple rounding function, could use enhancing, taken from OpenERP Code
    @return float'''
    if not round_:
        return factor
    return round(factor / round_) * round_

class bom_dimension_map(osv.osv):
    'BoM Template Variant Dimension Match'
    _name = 'bom.dimension_map'
    _description = __doc__

    _columns = {
        'name': fields.char('Name', size=64),
        'mapping_type': fields.selection([('one2one', 'Same Variants One -> One'),
                                          ('one2diff', 'Different Variants - One -> One Mapping')],
                                         'Mapping Type', required=True),
        'bom_tmpl_id': fields.many2many('mrp.bom', 'dim_map_mrp_bom_rel', 'dimension_map_id', 
                                        'bom_tmpl_id', 'BoM Templates'),
        'base_dimension_type': fields.many2one('product.variant.dimension.type', 
                                               'Base Dimension Type', required=True),
        'mapped_dimension_type': fields.many2one('product.variant.dimension.type',
                                                 'Mapped Dimension Type'),
        'match_opt_condition': fields.char('Match Condition', size=256, 
                                           help='Domain Expression to select which product should'
                                                ' be used, expressed on the product option \n'
                                                'The base variable is available which is the '
                                                'selected products dimension option'
                                                'e.g. [("name", "=", base.name)]'),        
    }

bom_dimension_map()

class bom_template(osv.osv):
    '''Implements BOM Template'''
    _inherit = 'mrp.bom'
    
    def _child_compute(self, cr, uid, ids, name, arg, context=None):
        """ Gets child bom.
        @param self: The object pointer
        @param cr: The current row, from the database cursor,
        @param uid: The current user ID for security checks
        @param ids: List of selected IDs
        @param name: Name of the field
        @param arg: User defined argument
        @param context: A standard dictionary for contextual values
        @return:  Dictionary of values
        """
        result = {}
        if context is None:
            context = {}
        bom_obj = self.pool.get('mrp.bom')
        bom_id = context and context.get('active_id', False) or False
        cr.execute('select id from mrp_bom')
        if all(bom_id != r[0] for r in cr.fetchall()):
            ids.sort()
            bom_id = ids[0]
        bom_parent = bom_obj.browse(cr, uid, bom_id, context=context)
        for bom in self.browse(cr, uid, ids, context=context):
            if (bom_parent) or (bom.id == bom_id):
                result[bom.id] = [x.id for x in bom.bom_lines]
            else:
                result[bom.id] = []
            if bom.bom_lines:
                continue
            if bom.product_id:
                ok = ((name=='child_complete_ids') and (bom.product_id.supply_method=='produce'))
            else:
                ok = ((name=='child_complete_ids') and (bom.product_tmpl_id.supply_method=='produce'))
            if (bom.type=='phantom' or ok):
                sids = bom_obj.search(cr, uid, [('bom_id', '=', False), 
                                                ('product_id', '=', bom.product_id and 
                                                                    bom.product_id.id),
                                                ('product_tmpl_id', '=', bom.product_tmpl_id and 
                                                                         bom.product_tmpl_id.id)]
                                      )
                if sids:
                    bom2 = bom_obj.browse(cr, uid, sids[0], context=context)
                    result[bom.id] += [x.id for x in bom2.bom_lines]
        return result

    def _compute_type(self, cr, uid, ids, field_name, arg, context=None):
        """ Sets particular method for the selected bom type.
        @param field_name: Name of the field
        @param arg: User defined argument
        @return:  Dictionary of values
        """
        res = dict([(x, '') for x in ids])
        for line in self.browse(cr, uid, ids, context=context):
            if line.type == 'phantom' and not line.bom_id:
                res[line.id] = 'set'
                continue
            if line.bom_lines or line.type == 'phantom':
                continue
            if line.product_id:
                if line.product_id.supply_method == 'produce':
                    if line.product_id.procure_method == 'make_to_stock':
                        res[line.id] = 'stock'
                    else:
                        res[line.id] = 'order'
            elif line.product_tmpl_id:
                if line.product_tmpl_id.supply_method == 'produce':
                    if line.product_tmpl_id.procure_method == 'make_to_stock':
                        res[line.id] = 'stock'
                    else:
                        res[line.id] = 'order'
        return res
    
    _columns = {
        'bom_template': fields.boolean('Template', help="If this field is set to True it matches "\
                                                        "the products based on the template"),
        'product_id': fields.many2one('product.product', 'Product', required=False),
        'child_complete_ids': fields.function(_child_compute, relation='mrp.bom', method=True, 
                                              string="BoM Hierarchy", type='many2many'),
        'method': fields.function(_compute_type, string='Method', method=True, type='selection', 
                                  selection=[('',''),('stock','On Stock'),
                                             ('order','On Order'),('set','Set / Pack')]),
        'product_tmpl_id': fields.many2one('product.template', 'Product Template'),
        'dimension_map_ids': fields.many2many('bom.dimension_map', 'dim_map_mrp_bom_rel',
                                              'bom_tmpl_id', 'dimension_map_id',
                                              'BoM Variant Dimensions Match'),
        'match_condition': fields.char('Match Condition', size=256, 
                                       help='Domain Expression if this product should be used, '
                                            'expressed on the product object'
                                            'e.g. [("name", "ilike", "frilly"), '
                                                  '("name", "ilike", "DD")]'),
        
                
    }

    def onchange_product_tmpl_id(self, cr, uid, ids, product_tmpl_id, name, context=None):
        """ Changes UoM and name if product_tmpl_id changes.
        @param name: Name of the field
        @param product_tmpl_id: Changed product_id
        @return:  Dictionary of changed values
        """
        if context is None:
            context = {}
            context['lang'] = self.pool.get('res.users').browse(cr, uid, uid).context_lang
        if product_tmpl_id:
            prod = self.pool.get('product.template').browse(cr, uid, product_tmpl_id, 
                                                            context=context)
            val = {'name': prod.name, 'product_uom': prod.uom_id.id, 'product_id': False}
            return {'value': val}
        return {}

    def onchange_product_id(self, cr, uid, ids, product_id, name, context=None):
        """ Changes UoM and name if product_id changes.
        @param name: Name of the field
        @param product_id: Changed product_id
        @return:  Dictionary of changed values
        """
        if context is None:
            context = {}
            context['lang'] = self.pool.get('res.users').browse(cr, uid, uid).context_lang
        if product_id:
            prod = self.pool.get('product.product').browse(cr, uid, product_id, 
                                                            context=context)
            val = {'name': prod.name, 'product_uom': prod.uom_id.id, 'product_tmpl_id': False}
            return {'value': val}
        return {}
    
    def _bom_find(self, cr, uid, product_id, product_uom, properties=None):
        """ Finds BoM for particular product and product uom.
        @param product_id: Selected product.
        @param product_uom: Unit of measure of a product.
        @param properties: List of related properties.
        @return: False or BoM id.
        """
        if properties is None:
            properties = []
        result = super(bom_template, self)._bom_find(cr, uid, product_id, product_uom, properties)
        if result:
            return result
        product_tmpl_id = self.pool.get('product.product').browse(cr, uid, 
                                                                  product_id).product_tmpl_id.id   
        cr.execute('select id from mrp_bom where product_tmpl_id=%s '
                   'and bom_id is null order by sequence', (product_tmpl_id,))
        ids = [x[0] for x in cr.fetchall()]
        max_prop = 0
        result = False
        for bom in self.pool.get('mrp.bom').browse(cr, uid, ids):
            prop = 0
            for prop_id in bom.property_ids:
                if prop_id.id in properties:
                    prop += 1
            if (prop > max_prop) or ((max_prop == 0) and not result):
                result = bom.id
                max_prop = prop
        return result
    
    def _bom_explode(self, cr, uid, bom, factor, product_id, orig_product_id=False,
                       properties=None, addthis=False, level=0):
        """ Finds Products and Workcenters for related BoM for manufacturing order.
        @param bom: BoM of particular product.
        @param factor: Factor of product UoM.
        @param properties: A List of properties Ids.
        @param addthis: If BoM found then True else False.
        @param level: Depth level to find BoM lines starts from 10.
        @return: result: List of dictionaries containing product details.
                 result2: List of dictionaries containing workcenter details.
        @note: Is a cut and paste from OpenERP function in mrp with addition of product_id parameter.
        Parameter added as when working with templates we cannot know the product_id.
        """
        if properties is None:
            properties = []
        prod_obj = self.pool.get('product.product')
        factor = factor / (bom.product_efficiency or 1.0)
        factor = rounding(factor, bom.product_rounding)
        if factor < bom.product_rounding:
            factor = bom.product_rounding
        result = []
        result2 = []
        phantom = False
        if bom.type == 'phantom' and not bom.bom_lines: #If it is a phantom bom with no lines
            newbom = self._bom_find(cr, uid, bom.product_id.id, bom.product_uom.id, properties)
            if newbom:
                res = self._bom_explode(cr, uid, self.browse(cr, uid, [newbom])[0], 
                                        factor*bom.product_qty, product_id, properties, 
                                        addthis=True, level=level+10)
                result = result + res[0]
                result2 = result2 + res[1]
                phantom = True
            else:
                phantom = False
        if not phantom:
            if addthis and not bom.bom_lines: #if its a leaf with no more lines
                if bom.bom_template: #we need to know the product first
                    product_id = prod_obj.browse(cr, uid, product_id)
                    result.append(
                    {
                        'name': product_id.name,
                        'product_id': product_id.id,
                        'product_qty': bom.product_qty * factor,
                        'product_uom': bom.product_uom.id,
                        'product_uos_qty': bom.product_uos and bom.product_uos_qty * 
                                           factor or False,
                        'product_uos': bom.product_uos and bom.product_uos.id or False,
                    })
                elif bom.match_condition:
                    matching_ids = prod_obj.search(cr, uid, eval(bom.match_condition))
                    if orig_product_id in matching_ids:
                        result.append(
                        {
                            'name': bom.product_id.name,
                            'product_id': bom.product_id.id,
                            'product_qty': bom.product_qty * factor,
                            'product_uom': bom.product_uom.id,
                            'product_uos_qty': bom.product_uos and bom.product_uos_qty *
                                               factor or False,
                            'product_uos': bom.product_uos and bom.product_uos.id or False,
                        })
                    
                else:
                    result.append(
                    {
                        'name': bom.product_id.name,
                        'product_id': bom.product_id.id,
                        'product_qty': bom.product_qty * factor,
                        'product_uom': bom.product_uom.id,
                        'product_uos_qty': bom.product_uos and bom.product_uos_qty *
                                           factor or False,
                        'product_uos': bom.product_uos and bom.product_uos.id or False,
                    })
            if bom.routing_id:
                for wc_use in bom.routing_id.workcenter_lines:
                    wc = wc_use.workcenter_id
                    div, mod = divmod(factor, wc_use.workcenter_id.capacity_per_cycle)
                    mult = (div + (mod and 1.0 or 0.0))
                    cycle = mult * wc_use.cycle_nbr
                    result2.append({
                        'name': tools.ustr(wc_use.name) + ' - '  + tools.ustr(bom.product_id.name),
                        'workcenter_id': wc.id,
                        'sequence': level+(wc_use.sequence or 0),
                        'cycle': cycle,
                        'hour': float(wc_use.hour_nbr*mult + ((wc.time_start or 0.0) + 
                                                              (wc.time_stop or 0.0) + 
                                                              cycle*(wc.time_cycle or 0.0)) * 
                                      (wc.time_efficiency or 1.0)),
                    })
            for bom2 in bom.bom_lines:
                if bom2.bom_template:
                    dim_option_obj = self.pool.get('product.variant.dimension.option')
                       
                    orig_variant_option_ids = [x.option_id.id for x in prod_obj.browse(
                                                    cr, uid, product_id).dimension_value_ids]
                    product_ids = set(prod_obj.search(cr, uid, [('product_tmpl_id', '=', 
                                                                 bom2.product_tmpl_id.id)]))
                    for dim_map in bom2.dimension_map_ids:
                        #iterate over dimension maps
                        base_option = dim_option_obj.search(
                                            cr, uid,[
                                            ('dimension_id', '=', dim_map.base_dimension_type.id), 
                                            ('id', 'in', orig_variant_option_ids)
                                            ])
                        
                        if base_option and isinstance(base_option, list):
                            base_option = base_option[0]
                        
                        if dim_map.mapping_type == 'one2one':
                            search_option_id = base_option
                            
                        elif dim_map.mapping_type == 'one2diff':
                            base = dim_option_obj.browse(cr, uid, base_option)
                            search_option_id = dim_option_obj.search(
                                                        cr, uid, eval(dim_map.match_opt_condition) + 
                                                        [('dimension_id', '=', dim_map.mapped_dimension_type.id)]
                                                        )
                            if len(search_option_id) == 1:
                                search_option_id = search_option_id[0]
                            elif search_option_id:
                                raise osv.except_osv(_('Error!'), 
                                                     _('More than one mapped dimension value '
                                                       'matched the search condition'))
                            else:
                                raise osv.except_osv(_('Error!'), 
                                                     _('No mapped dimension values '
                                                       'matched the search condition'))
                        if search_option_id:    
                            cr.execute(
                                'select pp.product_id from product_product_dimension_rel as pp '
                                'left join product_variant_dimension_value as dv '
                                'on pp.dimension_id=dv.id '
                                'where pp.product_id in %s and dv.option_id = %s', 
                                (tuple(product_ids), search_option_id)
                                )
                            res = (x[0] for x in cr.fetchall()) #should be a set of product_ids
                            product_ids.intersection_update(res)
                    if not product_ids or len(product_ids) != 1:
                        raise osv.except_osv(_('Error'), _('No matching product found!'))
                    product_id2 = list(product_ids)[0]          
                else:
                    product_id2 = bom2.product_id.id
                
                res = self._bom_explode(cr, uid, bom2, factor, product_id2, product_id, 
                                        properties, addthis=True, level=level+10)
                result = result + res[0]
                result2 = result2 + res[1]
        return result, result2
    
    def _check_recursion(self, cr, uid, ids, context=None):
        return super(bom_template, self)._check_recursion(cr, uid, ids, context=context)

    def _check_product(self, cr, uid, ids, context=None):
        all_prod = []
        all_prod_tmpl = []
        boms = self.browse(cr, uid, ids, context=context)
        def check_bom(boms):
            res = True
            for bom in boms:
                if bom.bom_template:
                    if bom.product_tmpl_id and bom.product_tmpl_id.id in all_prod_tmpl:
                        res = res and False
                    all_prod_tmpl.append(bom.product_tmpl_id.id)
                    lines = bom.bom_lines
                    if lines:
                        res = res and check_bom([bom_id for bom_id in lines if bom_id not in boms])
                else:
                    if bom.product_id and bom.product_id.id in all_prod:
                        res = res and False
                    all_prod.append(bom.product_id.id)
                    lines = bom.bom_lines
                    if lines:
                        res = res and check_bom([bom_id for bom_id in lines if bom_id not in boms])
            return res
        return check_bom(boms)
    
    _constraints = [
        (_check_recursion, 'Error ! You cannot create recursive BoM.', ['parent_id']),
        (_check_product, 'BoM line product should not be same as BoM product.', ['product_id']),
    ]
    
bom_template()

class mrp_production(osv.osv):
    _inherit = 'mrp.production'
    
    def action_compute(self, cr, uid, ids, properties=None, context=None):
        """ Computes bills of material of a product.
        @param properties: List containing dictionaries of properties.
        @return: No. of products.
        @note: Straight cut and paste, had to insert product_id in to _bom_find and
        _bom_explode calls.  Also because no super call is made, mrp_operations call
        added to end
        """
        if properties is None:
            properties = []
        results = []
        bom_obj = self.pool.get('mrp.bom')
        prod_line_obj = self.pool.get('mrp.production.product.line')
        workcenter_line_obj = self.pool.get('mrp.production.workcenter.line')
        
        for production in self.browse(cr, uid, ids):
            cr.execute('delete from mrp_production_product_line where production_id=%s', 
                       (production.id,))
            cr.execute('delete from mrp_production_workcenter_line where production_id=%s', 
                       (production.id,))
            bom_point = production.bom_id
            bom_id = production.bom_id.id
            if not bom_point:
                bom_id = bom_obj._bom_find(cr, uid, production.product_id.id, 
                                           production.product_uom.id, properties)
                if bom_id:
                    bom_point = bom_obj.browse(cr, uid, bom_id)
                    self.write(cr, uid, [production.id], 
                               {'bom_id': bom_id, 'routing_id': bom_point.routing_id.id or False})

            if not bom_id:
                raise osv.except_osv(_('Error'), _("Couldn't find bill of material for product"))

            factor = (production.product_qty * 
                      production.product_uom.factor_inv / 
                      bom_point.product_uom.factor)
            
            results, results2 = bom_obj._bom_explode(
                                    cr, uid, bom_point, factor / bom_point.product_qty, 
                                    production.product_id.id, production.product_id.id, 
                                    properties
                                    )
            for line in results:
                line['production_id'] = production.id
                prod_line_obj.create(cr, uid, line)
            for line in results2:
                line['production_id'] = production.id
                workcenter_line_obj.create(cr, uid, line)
        self._compute_planned_workcenter(cr, uid, ids, context={})
        return len(results)

mrp_production()


class product_variant_dimension_option(osv.osv):
    _name = 'product.variant.dimension.option'
    _inherit = 'product.variant.dimension.option'

    _columns = {
        'related_options': fields.many2many('product.variant.dimension.option', 'option_option_rel', 'from_option_id',
                                            'to_option_id', 'Related Options'),
    }

product_variant_dimension_option()





