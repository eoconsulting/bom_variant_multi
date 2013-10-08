MRP Bill of Material Templates
==============================

**This project has been moved to https://launchpad.net/~eoc**

This module implements BOM templates, more analogous to account templates than product templates.

A BOM template is created which then creates the associated BOM's. For any bom line you may specify a 
product template with one of 2 match types One 2 One (simple case) of One Dimension to a different dimension
where you must specify a match condition (formed as a domain expression on the dimension option object).

Most of the time the simple case is fine, however when mapping different variants, it pays to use a consistent naming
scheme.  Examples where this may be the case is say you can get a material in a certain range of colours, and paint in 
a lot more colours so you have 2 different variant dimensions.  By giving each colour the exact same name, or code, or
sequence number you can match differing dimensions.

Alternatively where you specify a product in a bom line you can optionally specify a match expression on the
product object which if met will add the product to the bom, otherwise it will not.  e.g say you have a variant of
knickers, called frilly knickers, which calls for a quantity of lace then you can match that and if not the lace will
not be added.

Also this module allow you to create a Manufacturing Order without BOM.

This software was original writed by **O4SB**, and was patched by **Enterprise Objects Consulting** some issues
and new features.

This sources are available in https://github.com/eoconsulting/bom_variant_multi

__________

[Enterprise Objects Consulting](http://www.eoconsulting.com.ar)
