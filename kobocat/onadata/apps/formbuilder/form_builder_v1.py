# -*- coding: utf-8 -*-
"""Demonstrate high quality docstrings.
This script runs to generate forms html code from parsed database
representation of xls form. Basically When we are uncomfortable to use
 Enketo any project this script can come handy.
"""
import psycopg2
from collections import OrderedDict
import AdvancedHTMLParser  # pylint: disable=import-error
import re
import codecs
import requests
import json

CONSTRAINT_REPLACE_DICT = {
    'and': '&&',
    'AND': '&&',
    'or': '||',
    'OR': '||',
    '${': 'vms.model.',
    '}': '[$index]',
    '=': '=='
}

STRING_LENGTH_RELEVANCE_REPLACE = {
    'string-length(': '',
    '${': 'vms.model.',
    '}': '[$index]',
    'and': '&&',
    'AND': '&&',
    'or': '||',
    'OR': '||',
    ')': '.length'
}

SELECTED_RELEVANCE_REPLACE = {
    'selected(': '',
    ')': '',
    '}': '[$index]',
    'and': '&&',
    'AND': '&&',
    'or': '||',
    'OR': '||',
    ',': '=='
}

CONNECTION = psycopg2.connect("host='192.168.19.15' dbname='sajida' user='kobo' password='kobo'")

XFORM_ID = 631
DOMDICT = OrderedDict()
REPEAT_GROUP_HEADERS = []
GLOBAL_ANGULAR_CONTAINERS = ''
C = 0


def __db_fetch_values(query):
    """
        Fetch database result set as list of tuples

        Args:
            query (str): raw query string

        Returns:
            str: Returns database result set as list of tuples
    """
    cursor = CONNECTION.cursor()
    cursor.execute(query)
    fetch_val = cursor.fetchall()
    cursor.close()
    return fetch_val


def __db_fetch_single_value(query):
    """
        Fetch database result of single field as string

        Args:
            query (str): raw query string

        Returns:
            str: Returns database result of single field as string
    """
    cursor = CONNECTION.cursor()
    cursor.execute(query)
    fetch_val = cursor.fetchone()
    cursor.close()
    return fetch_val[0]


def __db_fetch_values_dict(query):
    """
        Fetch database result set as list of ordereddict

        Args:
            query (str): raw query string

        Returns:
            str: Returns database result set as list of ordereddict
    """
    cursor = CONNECTION.cursor()
    cursor.execute(query)
    desc = cursor.description
    fetch_val = [
        OrderedDict(zip([col[0] for col in desc], row))
        for row in cursor.fetchall()]
    cursor.close()
    return fetch_val


def __db_fetch_row_count(query):
    """
        Fetch database result set row count

        Args:
            query (str): raw query string

        Returns:
            str: Returns database result set row count
    """
    cursor = CONNECTION.cursor()
    cursor.execute(query)
    row_count = cursor.rowcount
    return row_count


def generate_html_fields(field_data, root):
    """
        Generate Indivudual Field Html data

        Args:
            field_data (list): returned row data from query.
            root (str): root element of form block.

        Returns:
            str: Returns a single input form data html as string
    """
    k = 0
    while k < len(field_data):
        if field_data[k] is not None and type(field_data[k]) is str:
            field_data[k] = field_data[k].decode('utf-8')
        k = k + 1

    return '<div class="col-lg-3"><div ' + str(generate_relevance_code(field_data[5], root)) \
           + ' class="form-group">' \
           + get_label_part(field_data[2]) + '' \
           + get_input_part([field_data[3], field_data[0],
                             field_data[2], field_data[5], field_data[4], root]) + '</div></div>'


def get_date_appearance(appearance):
    """
        Generate datepicker-popup format
        Arg:
            appearance (dict) : appearance logic in json format from xls form

        Returns:
             str: returns datepicker-popup format for angular ui datepicker
    """
    if appearance and appearance.has_key('appearance'):
        ap_key = appearance['appearance'].split(' ')[0]
        if ap_key == 'month-year':
            date_format = 'MM/yyyy'
        elif ap_key == 'year':
            date_format = 'yyyy'
        else:
            date_format = 'yyyy/MM/dd'
    else:
        date_format = 'yyyy/MM/dd'

    return ' datepicker-popup="' + date_format + '"'


def generate_relevance_code(relevance, root):
    """
        Generate relevance logic codes

        Args:
            relevance (dict): relevance logic in json format from xls form.
            root (str): root element of form block.

        Returns:
            str: Returns a relevence section of input field html
    """
    relevance_str = ''
    if relevance is not None:
        if relevance.has_key('relevant'):
            if relevance['relevant'].startswith('string-length'):
                if root == 'root':
                    relevance_str = 'ng-show="' + replace_all(relevance['relevant'],
                                                              STRING_LENGTH_RELEVANCE_REPLACE) + '"'
                else:
                    relevance_str = 'ng-show="' + relevance['relevant'].replace('string-length(', '', ).replace(')',
                                                                                                                '.length').replace(
                        '${', 'vms.model.' + root + '__').replace('}',
                                                                  '[$index]').replace(
                        '=', '==').replace('and', '&&').replace('or', '||').replace('AND', '&&').replace('OR',
                                                                                                         '||') + '"'
            elif relevance['relevant'].startswith('selected'):
                if root == 'root':
                    relevance_str = 'ng-show="' + replace_all(relevance['relevant'].replace('${', 'vms.model.'),
                                                              SELECTED_RELEVANCE_REPLACE) + '"'
                else:
                    relevance_str = 'ng-show="' + replace_all(
                        relevance['relevant'].replace('${', 'vms.model.' + root + '__'),
                        SELECTED_RELEVANCE_REPLACE) + '"'
            else:
                if root == 'root':
                    relevance_str = 'ng-show="' + replace_all(relevance['relevant'], CONSTRAINT_REPLACE_DICT) + '"'
                else:
                    relevance_str = 'ng-show="' + relevance['relevant'].replace('${',
                                                                                'vms.model.' + root + '__').replace('}',
                                                                                                                    '[$index]').replace(
                        '=', '==').replace('and', '&&').replace('or', '||').replace('AND', '&&').replace('OR',
                                                                                                         '||') + '"'
    return relevance_str


def generate_ngchange_part(data_source, field_name, child_field):
    """
        Generate ng-change codes angular functionality for select fields

        Args:
            data_source (str): The url to hit for asynchronus loading of option data.
            field_name (unicode): current field in processing queue.
            child_field (str): impact field name of ng-change event

        Returns:
            str: Returns html code of enabling angular functionality of ng-change event
    """
    global GLOBAL_ANGULAR_CONTAINERS
    ng_model_name = 'vms.model.' + field_name.replace('/', '__')
    options_container_name = 'opt_' + child_field.replace('/', '__')
    GLOBAL_ANGULAR_CONTAINERS += '$scope.opt_' + options_container_name + ' = [];'
    return 'ng-change="getExternalOptions(\'' + data_source + '\',' \
           + ng_model_name + ', \'' + options_container_name + '\')"'


def generate_ngoptions_part(field_name):
    """
        Generate ng-option codes angular functionality for select fields

        Args:
            field_name (unicode): current field in processing queue.

        Returns:
            str: Returns html code of enabling angular functionality of ng-options
    """
    options_container_name = 'opt_' + field_name.replace('/', '__')
    return 'ng-options="option.value as option.name for option in ' + options_container_name + '"'


def get_input_part(field_details):
    """
        Generate core input part of form html

        Args:
            field_type (str): type of field according to xls convention
            field_name (str): current field in processing queue.
            field_label (str): field label text
            field_bind (str): Bind logic of xls form fro this specific field
            root (str): root element of form block.
        Returns:
            str: Returns html code of total input field
    """
    field_type = field_details[0]
    field_name = field_details[1]
    field_label = field_details[2]
    field_bind = field_details[3]
    field_cntrl = field_details[4]
    root = field_details[5]

    select_change_part = ''
    select_option_part = ''
    child_field = get_child_filter_field(field_name)
    if child_field:
        # Rubbish ..... :@ :@
        data_source = __db_fetch_single_value(
            "select data_source from xform_extracted_test where field_name = '" + str(child_field[0][0]) + "'")
        select_change_part = generate_ngchange_part(data_source, field_name, child_field[0][0])

    parent_field = get_parent_filter_field(field_name)
    if parent_field is not None:
        select_option_part = generate_ngoptions_part(field_name)

    field_name = field_name.replace("/", "__")  # replace slash with underscore for dom manipulation purpose
    constraint_bind_part = generate_validation_logics(field_name, field_bind, root)  # get validation logic code

    if root == 'root':
        classic_field_name = field_name
    else:
        classic_field_name = field_name + '__{{$index}}'

    input_part = ''
    name_part = get_name_part(field_name, root)
    model_part = get_model_part(field_name, root)
    if field_type == 'text':
        input_part = '<input ' + name_part + ' type="text" ' + constraint_bind_part + ' class ="form-control" ' + model_part + ' validation-error-to="' + classic_field_name + '_error"><span class="field_error" id="' + classic_field_name + '_error"></span>'
    elif field_type == 'integer':
        input_part = '<input ' + name_part + ' type="number" ' + constraint_bind_part + ' class ="form-control" ' + model_part + ' validation-error-to="' + classic_field_name + '_error"><span  class="field_error" id="' + classic_field_name + '_error"></span>'
    elif field_type == 'decimal':
        input_part = '<input ' + name_part + ' type="number" step="0.01" ' + constraint_bind_part + ' class ="form-control" ' + model_part + ' validation-error-to="' + classic_field_name + '_error"><span  class="field_error" id="' + classic_field_name + '_error"></span>'
    elif field_type == 'select one':
        input_part = '<select ' + select_option_part + ' ' + select_change_part + ' ' + name_part + ' class="form-control" ' + constraint_bind_part + ' validation-error-to="' + classic_field_name + '_error"  ' + model_part + '>' + get_select_options(
            field_name,
            field_label) + '</select><span class="field_error" id="' + classic_field_name + '_error"></span>'
    elif field_type == 'select all that apply':
        input_part = '<multiselect ' + name_part + ' data-multiple="true" options="c.id as c.name for c in ' + generate_multiple_options(
            field_name) + '" ' + constraint_bind_part + ' validation-error-to="' + classic_field_name + '_error" class="form-control"  ' + model_part + '></multiselect><span class="field_error" id="' + classic_field_name + '_error"></span>'
    elif field_type == 'date':
        input_part = '<div class="input-group"><input ' + name_part + ' type="text" class ="datepicker form-control"  ' + model_part + ' ' + constraint_bind_part + ' validation-error-to="' + classic_field_name + '_error" ' + get_date_appearance(
            field_cntrl) + ' datepicker-options="vms.dateOptions" datepicker-mode="day" is-open="vms.isDatePickerOpen_' + field_name + '" min-date="vms.minDate" max-date="vms.maxDate" readonly><span class="input-group-btn"> <button type="button" class="btn btn-default" data-ng-click="vms.openDatePicker($event,\'isDatePickerOpen_' + field_name + '\')"> <i class="glyphicon glyphicon-calendar"></i></button></span></div><span class="field_error" id="' + classic_field_name + '_error"></span>'
    elif field_type == 'photo':
        input_part = '<input type="file" ngf-select ' + model_part + ' ' + name_part + ' ngf-max-size="20MB">'
    return input_part


def get_label_part(field_label):
    """
        Generate input field label

        Args:
            field_label (str): field label from xls form for current field in processing queue.

        Returns:
            str: Returns html code of field label
    """
    if field_label is not None:
        return '<label>' + field_label + '</label>'
    else:
        return ''


def get_name_part(field_name, root):
    """
        Generate input name part

        Args:
            field_name (str): current field in processing queue.
            root (str): root element of form block.

        Returns:
            str: Returns html code for input field name part
    """
    if root == 'root':
        return ' name="' + field_name + '"'
    else:
        return ' name="' + field_name + '__{{$index}}" '


def get_model_part(field_name, root):
    """
        Generate input ngModel html code

        Args:
            field_name (str): current field in processing queue.
            root (str): root element of form block.

        Returns:
            str: Returns html code for ngModel part of angular functionality
    """
    if root == 'root':
        return 'ng-model="vms.model.' + field_name + '"'
    else:
        return 'ng-model="vms.model.' + field_name + '[$index]"'


def get_child_filter_field(field_name):
    """
        fetch child field of a select one type field

        Args:
            field_name (str): current field in processing queue.

        Returns:
            str: Returns child field name
    """
    check_query = "select field_name from public.xform_extracted_test where parent_filter = '" + str(
        field_name) + "' and xform_id = " + str(XFORM_ID)
    check_data = __db_fetch_values(check_query)
    row_count = __db_fetch_row_count(check_query)
    if check_data and row_count == 1:
        return check_data
    else:
        return None


def get_parent_filter_field(field_name):
    """
        fetch parent field of a select one type field

        Args:
            field_name (str): current field in processing queue.

        Returns:
            str: Returns parent field name
    """
    check_query = "select parent_filter from public.xform_extracted_test where field_name = '" + str(
        field_name) + "' LIMIT 1"

    data_source_query = "select data_source from public.xform_extracted_test where field_name = '" + str(
        field_name) + "' and xform_id = " + str(XFORM_ID) + " LIMIT 1"

    check_data = __db_fetch_single_value(check_query)
    data_source = __db_fetch_single_value(data_source_query)
    if check_data and data_source:
        return check_data


def get_select_options(field_name, field_label):
    """
        Generate select field options from xls parsed data

        Args:
            field_name (str): current field in processing queue.
            field_label (str): field label from xls form for current field in processing queue.

        Returns:
            str: Returns select field options
    """
    field_name = field_name.replace("__", "/")
    option_query = "SELECT value_text,value_label,field_detail,parent_filter,data_source FROM public.xform_extracted_test WHERE xform_id = " + str(
        XFORM_ID) + " AND field_name = '" + str(
        field_name) + "' ORDER BY sl_no"
    print option_query
    option_data = __db_fetch_values(option_query)

    options = '<option value="">-- Select --</option>'
    if option_data[0][4] is None:
        i = 0
        while i < len(option_data):
            if option_data[i][2].get("myfilter"):

                filter_text = 'ng-show="vms.model.' + option_data[i][3].replace('/', '__') + '==\'' + option_data[i][
                    2].get(
                    "myfilter") + '\'"'
            else:
                filter_text = ''
            options += '<option ' + filter_text + ' value="' + option_data[i][0].decode('utf-8') + '">' + \
                       option_data[i][
                           1].decode(
                           'utf-8') + '</option>'
            i += 1
    else:
        if option_data[0][3] is None:
            req = requests.get(option_data[0][4])
            for opt in req.json():
                options += '<option value="' + str(opt.get('value')).decode('utf-8') + '">' + str(
                    opt.get('name')).decode('utf-8') + '</option>'
    return options


def generate_multiple_options(field_name):
    """
        Generate select field options for multiple select field from xls parsed data

        Args:
            field_name (str): current field in processing queue.

        Returns:
            str: Returns js object for placing in multi select directive
    """
    global GLOBAL_ANGULAR_CONTAINERS
    field_name = field_name.replace("__", "/")
    option_query = "SELECT value_text,value_label FROM public.xform_extracted_test WHERE xform_id = " + str(
        XFORM_ID) + " AND field_name = '" + str(
        field_name) + "' ORDER BY sl_no"
    field_name = field_name.replace("/", "__")
    option_data = __db_fetch_values(option_query)
    option_list = []
    for opt in option_data:
        k = {}
        k['id'] = opt[0]
        k['name'] = opt[1]
        option_list.append(k)

    GLOBAL_ANGULAR_CONTAINERS += '$scope.' + field_name + '__multiselectOptions = ' + json.dumps(option_list) + ';'

    return field_name + '_multiselectOptions'


def get_appearance(appearance):
    """
        Generate select field options from xls parsed data

        Args:
            appearance (dict): appearance logic in json format from xls form.

        Returns:
            str: Returns html code for appearance for input fields
    """
    if appearance is not None and appearance['appearance'].startswith('w'):
        return 'class="form-group col-md-3" style="width:' + str(
            int(appearance['appearance'].split(' ')[0][1:]) * 10) + '% !important"'
    else:
        return 'class="form-group col-md-3"'


def generate_validation_logics(field_name, field_bind, root):
    """
        Generate validation code for input fields

        Args:
            field_name (str): current field in processing queue.
            field_bind (dict): Bind logic of xls form fro this specific field
            root (str): root element of form block.

        Returns:
            str: Returns html code for validation logic
    """
    field_name = field_name.replace("/", "__")
    validation_part = ''
    change_part = ''
    required_part = ''
    validation_part_list = []

    if field_bind is not None:
        if field_bind.has_key('jr:constraint_msg'):
            constraint_msg = field_bind['jr:constraint_msg']
        elif field_bind.has_key('jr:constraintMsg'):
            constraint_msg = field_bind['jr:constraintMsg']
        else:
            constraint_msg = 'Please enter a valid value'

        # check field is required
        if field_bind.has_key('required'):
            if not field_bind.has_key('constraint'):
                if field_bind['required'].lower() == 'yes' or field_bind['required'].lower() == 'true':
                    validation_part_list.append('required')

        # check field has constraints
        if field_bind.has_key('constraint'):
            if field_bind['constraint'].startswith('regex'):
                validation_part_list.append('pattern=/' + str(
                    re.findall("'([^\']*)'", field_bind['constraint'])[0]) + '/:alt=' + constraint_msg + '')
            elif field_bind['constraint'].startswith('.'):
                if root == 'root':
                    selected_instance = 'vms.model.' + field_name
                else:
                    selected_instance = 'vms.model.' + field_name + '[$index]'

                change_part = ' ng-change="parseCustomConstraints(' + selected_instance + ',\'' + str(
                    field_bind[
                        'constraint']) + '\', \'' + root + '\', {{$index}}, ' + field_name + ',' + constraint_msg + ')"'

        validation_part = 'validation="' + '|'.join(validation_part_list) + '"'
    return change_part + ' ' + validation_part + ' ' + required_part


def replace_all(text, dic):
    """
        Replace multiple occurances of multiple substring

        Args:
            text (str): string which to be replaced
            dic (dict): change parts as key(old part) ,value(replace part) in a dict

        Returns:
            str: Returns replaced string
    """
    for i, j in dic.iteritems():
        text = text.replace(i, j)
    return text


def generate_form_html(dom_data):
    """
        Generate total Html from parsed dom dictionary

        Args:
            dom_data (dict): Representation of dom data as dictionary

        Returns:
            str: returns form html
    """
    parser = AdvancedHTMLParser.AdvancedHTMLParser()
    for idx in dom_data:
        idx = idx.replace('/', '__')
        if idx == 'root':
            parser.parseStr('<div ng-controller="myCtrl as vms" id="mainDiv">' + dom_data[idx] + '</div>')
        else:
            if parser.getElementById('rpt_' + idx) is not None:
                parser.getElementById('rpt_' + idx).appendText(dom_data[idx])
            elif parser.getElementById('grp_' + idx) is not None:
                parser.getElementById('grp_' + idx).appendText(dom_data[idx])
    return parser.getHTML()


def fetch_extracted_xform_data(root):
    """
            generate dictonary representation of DOM data

            Args:
                root (str): root element of form block.

            Returns:
                void (instead save output to a global dictionary)
        """
    global DOMDICT, REPEAT_GROUP_HEADERS
    total_html = ''
    unique_fields = []
    sql_root = replace_all(root, {'__': '/'})
    fetch_query = "SELECT field_name, field_label, field_type, parent, value_text, value_label, xform_id, id, field_detail, is_extracted, sl_no, bind, cntrl,parent_filter, data_source FROM public.xform_extracted_test where xform_id = " + str(
        XFORM_ID) + " and parent = '" + str(
        sql_root) + "' and field_name not in ('username','meta','meta/instanceID','start','end') order by sl_no;"
    fetch_data = __db_fetch_values_dict(fetch_query)

    i = 0
    global C
    DOMDICT[root] = ''
    while i < len(fetch_data):
        if fetch_data[i].get("field_type") != 'repeat' and fetch_data[i].get("field_type") != 'group' and fetch_data[
            i].get("field_type") != 'note':
            if fetch_data[i].get("field_name") not in unique_fields:
                unique_fields.append(fetch_data[i].get("field_name"))
                if C % 4 == 0:
                    total_html += '<div class="container"><div class="row">'
                form_field = generate_html_fields(
                    [fetch_data[i].get("field_name"), root, fetch_data[i].get("field_label"),
                     fetch_data[i].get("field_type"), fetch_data[i].get('cntrl'), fetch_data[i].get('bind'),
                     fetch_data[i].get('parent_filter'), fetch_data[i].get('data_source')], root)
                C = C + 1
                if C % 4 == 1:
                    total_html += '</div></div>'
                total_html += form_field
            DOMDICT[root] = total_html
        else:
            if fetch_data[i].get("field_type") == 'repeat':
                REPEAT_GROUP_HEADERS.append(fetch_data[i].get("field_name"))
                fetch_extracted_xform_data(replace_all(fetch_data[i].get("field_name"), {'/': '__'}))
                repeat_div = '<div id="rpt_' + replace_all(fetch_data[i].get(
                    "field_name"),
                    {'/': '__'}) + '" class="iterator_fields" ng-repeat="name in data.names track by $index"></div>'
                total_html += repeat_div
                DOMDICT[root] = total_html
            elif fetch_data[i].get("field_type") == 'group':
                REPEAT_GROUP_HEADERS.append(fetch_data[i].get("field_name"))
                fetch_extracted_xform_data(replace_all(fetch_data[i].get("field_name"), {'/': '__'}))
                group_div = '<div id="grp_' + replace_all(fetch_data[i].get(
                    "field_name"), {'/': '__'}) + '" class="iterator_fields"></div>'
                total_html += group_div
                DOMDICT[root] = total_html
        i += 1
    return 0


def generate_item_tree(tree_data):
    """
        Generate dom tree for use in scripting part of form

        Args:
            tree_data (list): nested list of field parent data from xform_extracted table

        Returns:
            str: returns json structure
    """
    dom_tree = {}
    for i in range(0, len(tree_data)):
        dom_tree[tree_data[i][0].replace("/", "__")] = tree_data[i][1]
        codecs.open('hello.js', 'w', 'UTF-8').write(json.dumps(dom_tree))


TREE_QUERY = "SELECT field_name, parent FROM public.xform_extracted_test where xform_id = " + str(
    XFORM_ID) + " and field_name not in ('username','meta') and parent not in ('meta')"
TREE_DATA = __db_fetch_values(TREE_QUERY)
generate_item_tree(TREE_DATA)

fetch_extracted_xform_data('root')
print C
GENERATED_HTML = generate_form_html(DOMDICT)
NEW_PARSER = AdvancedHTMLParser.AdvancedHTMLParser()
NEW_PARSER.parseStr(GENERATED_HTML)

# for i in range(len(REPEAT_GROUP_HEADERS)):
#    if NEW_PARSER.getElementById('rpt_' + REPEAT_GROUP_HEADERS[i]) is not None:
#        NEW_PARSER.getElementById('rpt_' + REPEAT_GROUP_HEADERS[i]).appendText(
#            '<span ng-click="addRow($index)" ng-show="$last"><i class="fa fa-2x fa-plus-circle" aria-hidden="true"></i></span><span ng-click="deleteRow($event,name)" ng-show="$index != 0"><i class="fa fa-2x fa-minus-circle" aria-hidden="true"></i></span>')

# **************Generate HTML Code************
codecs.open('hello.html', 'w', 'UTF-8').write(NEW_PARSER.getHTML())
codecs.open('hello.js', 'a', 'UTF-8').write('\n\n' + GLOBAL_ANGULAR_CONTAINERS)
