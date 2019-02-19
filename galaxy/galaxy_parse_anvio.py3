#!/usr/bin/env python
# -*- coding: utf-8

"""A script to convert anvi'o python scripts to Galaxy Tools."""
import sys
import os
from xml.sax.saxutils import quoteattr

from jinja2 import Template

#sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir ) ) )#, 'anvi')))
sys.path.append( os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir ) ) )#, 'anvi')))

import anvio


ANVIO_VERSION = '5.3'#'2.1.0' #FIXME! change to real version

TOOLS_TO_SKIP = ["anvi-display-contigs-stats","anvi-init-bam", "anvi-display-structure", "anvi-self-test", "anvi-run-workflow"]
#anvi-self-test is kept, may be useful, it does launch a server and webbrowser, and then wait...so maybe not keep
#waits on anvi-display-contigs-stats, add a shutdown button for server?

ONLY_DO_TOOLS = []#["anvi-import-state"]

GALAXY_ANVIO_LOG_XML = '<data name="GALAXY_ANVIO_LOG" format="txt" label="${tool.name} on ${on_string}: Log"/>'

TOOL_TEMPLATE = """<tool id="{{id}}" name="{{name}}" version="{{version}}">
{%- if description %}
    <description>{{ description }}</description>
{%- endif %}
{%- if macros %}
    <macros>
        <import>macros.xml</import>
    </macros>
    <expand macro="requirements" />
    <expand macro="stdio" />
{%- if version_command %}
    <expand macro="version_command" />
{%- endif %}
{%- else %}
    <requirements>
{%- for requirement in requirements %}
        {{ requirement }}
{%- endfor %}
{%- for container in containers %}
        {{ container }}
{%- endfor %}
    </requirements>
    <stdio>
        <exit_code range="1:" />
    </stdio>
{%- if version_command %}
    <version_command>{{ version_command }}</version_command>
{%- endif %}
{%- endif %}
    <command><![CDATA[
{%- if command %}
        {{ command }}
{%- else %}
        TODO: Fill in command template.
{%- endif %}
    ]]></command>
    <inputs>
{%- for input in inputs %}
        {{ input }}
{%- endfor %}
    </inputs>
    <outputs>
{%- for output in outputs %}
        {{ output }}
{%- endfor %}
    </outputs>
{%- if tests %}
    <tests>
{%- for test in tests %}
        <test>
{%- for param in test.params %}
            <param name="{{ param[0]}}" value="{{ param[1] }}"/>
{%- endfor %}
{%- for output in test.outputs %}
            <output name="{{ output[0] }}" file="{{ output[1] }}"/>
{%- endfor %}
        </test>
{%- endfor %}
    </tests>
{%- endif %}
    <help><![CDATA[
{%- if help %}
        {{ help }}
{%- else %}
        TODO: Fill in help.
{%- endif %}
    ]]></help>
{%- if macros %}
    <expand macro="citations" />
{%- else %}
{%- if doi or bibtex_citations %}
    <citations>
{%- for single_doi in doi %}
        <citation type="doi">{{ single_doi }}</citation>
{%- endfor %}
{%- for bibtex_citation in bibtex_citations %}
        <citation type="bibtex">{{ bibtex_citation }}</citation>
{%- endfor %}
    </citations>
{%- endif %}
{%- endif %}
</tool>
"""

MACROS_TEMPLATE = """<macros>
    <xml name="requirements">
        <requirements>
{%- for requirement in requirements %}
        {{ requirement }}
{%- endfor %}
            <yield/>
{%- for container in containers %}
        {{ container }}
{%- endfor %}
        </requirements>
    </xml>
    <xml name="stdio">
        <stdio>
            <exit_code range="1:" />
        </stdio>
    </xml>
    <xml name="citations">
        <citations>
{%- for single_doi in doi %}
            <citation type="doi">{{ single_doi }}</citation>
{%- endfor %}
{%- for bibtex_citation in bibtex_citations %}
            <citation type="bibtex">{{ bibtex_citation }}</citation>
{%- endfor %}
            <yield />
        </citations>
    </xml>
{%- if version_command %}
    <xml name="version_command">
        <version_command>{{ version_command }}</version_command>
    </xml>
{%- endif %}
</macros>
"""

galaxy_tool_citation ='''@ARTICLE{Blankenberg19-anvio,
   author = {Daniel Blankenberg, et al},
   title = {In preparation..},
   }'''


SHED_YML ="""name: anvio
owner: blankenberg
description: "Anvi’o: an advanced analysis and visualization platform for ‘omics data"
homepage_url: https://github.com/merenlab/anvio
long_description: |
    Anvi’o is an analysis and visualization platform for ‘omics data. 
    It brings together many aspects of today’s cutting-edge genomic, metagenomic, and metatranscriptomic analysis practices to address a wide array of needs.
remote_repository_url: https://github.com/blankenberg/anvio-galaxy
type: unrestricted
categories:
- Metagenomics
auto_tool_repositories:
  name_template: "{{ tool_id }}"
  description_template: "Wrapper for the Anvi'o tool suite: {{ tool_name }}"
suite:
  name: "suite_anvio"
  description: "Anvi’o: an advanced analysis and visualization platform for ‘omics data"
  long_description: |
    Anvi’o is an analysis and visualization platform for ‘omics data. 
    It brings together many aspects of today’s cutting-edge genomic, metagenomic, and metatranscriptomic analysis practices to address a wide array of needs.
"""


class Parameter( object ):
    def __init__( self, name, arg_short, arg_long, info_dict ):
        self._name = name
        self.name = name.replace( "-", '_' )
        self.arg_short = arg_short
        self.arg_long = arg_long
        self.info_dict = info_dict
        self.required = info_dict.get( 'required', False )
        self.is_output = name.lower().startswith( 'output' )
        self.is_input = not self.is_output
    def copy(self, name=None, arg_short=None, arg_long=None, info_dict = None):
        orig_dict = self.info_dict.copy()
        if info_dict:
            orig_dict.update( info_dict )
        return self.__class__( name or self.name, arg_short or self.arg_short, arg_long or self.arg_long, orig_dict )
    def get_name( self ):
        return quoteattr( self.name )
    def get_output_cmd_name(self):
        return self.name
    def get_input_cmd_name(self):
        return self.name
    def get_type( self ):
        return 'text'
    def get_label( self ):
        return quoteattr( self.name.replace( '_', " " ).title() )
    def get_default( self ):
        default = self.info_dict.get( 'default', None )
        if default is None:
            default = ''
        return quoteattr( str( default ) )
    def get_argument( self ):
        return quoteattr( self.arg_long )
    def is_positional_arg( self ):
        return not ( self.arg_short or self.arg_long )
    def get_arg_text( self ):
        arg = self.arg_long or self.arg_short or ''
        return arg
    def get_help( self ):
        #print(self.info_dict)
        #print(self.info_dict.get('help', ''))
        help = self.info_dict.get('help', '')
        #if 'default' not in self.info_dict and '%(default)' in help:
        #    print('MISSING DEFAULT!')
        #    self.info_dict['default'] = None
        #help = help % self.info_dict
        #FIX FOR NOT DEFINED DEFAULT IN HELP TEXT
        help = help.format(**self.info_dict)
        help = help.replace( '\n', ' ' ).replace( '\r', ' ' ).replace( '\t', ' ' ).strip()
        while '  ' in help:
            help = help.replace( '  ', ' ' )
        return quoteattr( help )
    def get_optional( self ):
        if self.info_dict.get( 'required', False ):
            return 'False'
        return 'True'
    def to_xml_param( self ):
        return """<param name=%s type="%s" label=%s value=%s optional="%s" argument=%s help=%s/>""" % \
            (
                quoteattr( self.get_input_cmd_name() ), 
                self.get_type(),  
                self.get_label(), 
                self.get_default(), 
                self.get_optional(),
                self.get_argument(), 
                self.get_help(),

            )
    def to_xml_output( self ):
        return ''
    def get_pre_cmd_line( self ):
        return ''
    def get_post_cmd_line( self ):
        return ''
    def to_cmd_line( self ):
        text = ''
        cmd_txt =  "%s '${%s}'" % ( self.get_arg_text(), self.get_input_cmd_name() )
        if not self.required:
            text = """
#if $str( $%s ):
    %s
#end if\n""" % ( self.get_input_cmd_name(), cmd_txt )
        else:
            text = "%s\n" % cmd_txt
        return text
    def __str__( self ):
        return "%s\n%s\n" % ( self.to_xml_param(), self.to_cmd_line() )


class ParameterDiscard( Parameter ):
    def get_type(self):
        return "string"
    def to_xml_param( self ):
        return ''
    def to_cmd_line( self ):
        return ''

class ParameterBooleanAlwaysTrue( Parameter ):
    def get_type(self):
        return "boolean"
    def to_xml_param( self ):
        return ''
    def to_cmd_line( self ):
        return self.arg_long


class ParameterBoolean( Parameter ):
    def get_type(self):
        return "boolean"
    def to_xml_param( self ):
        return """<param name=%s type="%s" label=%s truevalue="%s" falsevalue="" checked=%s optional="%s" argument=%s help=%s/>""" % \
            (
                self.get_name(), 
                self.get_type(),  
                self.get_label(),
                self.arg_long,
                self.get_default(), 
                self.get_optional(),
                self.get_argument(), 
                self.get_help(),

            )
    def to_cmd_line( self ):
        return "${%s}\n" % ( self.name )


class ParameterINT( Parameter ):
    def get_type(self):
        return "integer"

class ParameterFLOAT( Parameter ):
    def get_type(self):
        return "float"

class ParameterNUM_CPUS( ParameterINT ):
    def to_xml_param( self ):
        return ''
    def to_cmd_line( self):
        return '%s "\\${GALAXY_SLOTS:-1}"\n' % ( self.get_arg_text() )

class ParameterFILE_PATH( Parameter ):
    def __init__( self, *args, **kwd ):
        super( ParameterFILE_PATH, self ).__init__( *args, **kwd )
        self.multiple = False
        if self.info_dict.get( 'nargs', None ) == '+':
            self.multiple = True
    def get_type(self):
        return "data"
    def get_format( self ):
        return "txt"
    def get_multiple( self ):
        return self.multiple
    def get_output_label( self ):
        return quoteattr( '${tool.name} on ${on_string}: %s' % ( self.name.replace( '_', " " ).title() ) )
    def to_xml_param( self ):
        return """<param name=%s type="%s" label=%s format="%s" optional="%s" multiple="%s" argument=%s help=%s/>""" % \
            (
                quoteattr( self.get_input_cmd_name() ), 
                self.get_type(),  
                self.get_label(), 
                self.get_format(), 
                self.get_optional(),
                self.get_multiple(),
                self.get_argument(), 
                self.get_help(),
            )
    def get_format_source(self):
        return 'format_source="input_%s"' % ( self.name )
        if ',' in self.get_format():
            return 'format_source="input_%s"' % ( self.name )
        return ''
    def get_metadata_source(self):
        return 'metadata_source="input_%s"' % ( self.name )
        if ',' in self.get_format():
            return 'format_source="input_%s"' % ( self.name )
        return ''
    def to_xml_output( self ):
        #print ('toxml putput', self.name, self.get_format() ) 
        return """<data name=%s format="%s" %s %s label=%s/>""" % \
            (
                quoteattr(self.get_output_cmd_name() ), 
                self.get_format().split(',')[0],
                self.get_format_source(),
                self.get_metadata_source(),
                self.get_output_label(),
            )
    def to_cmd_line( self ):
        text = ''
        cmd_txt =  "%s '${%s}'" % ( self.get_arg_text(), self.get_input_cmd_name() )
        if not self.required:
            text = """
#if $%s:
    %s
#end if\n""" % ( self.get_input_cmd_name(), cmd_txt )
        else:
            text = "%s\n" % cmd_txt
        return text


class ParameterREPORT_FILE_PATH( ParameterFILE_PATH ):
    def __init__( self, *args, **kwd ):
        super( ParameterREPORT_FILE_PATH, self ).__init__( *args, **kwd )
        self.is_input = False
        self.is_output = True


class ParameterDB( ParameterFILE_PATH ):
    def __init__( self, *args, **kwd ):
        super( ParameterDB, self ).__init__( *args, **kwd )
        self.is_output = True
        self.is_input = not self.name.startswith( 'output' )
        print('is_input', self.name, self.is_input)
    def get_format( self ):
        return "anvio_db"
    def to_cmd_line( self ):
        if self.is_input:
            return  "%s '${%s}'\n" % ( self.get_arg_text(), self.get_output_cmd_name() )
        else:
            return  "%s '%s.db'\n" % ( self.get_arg_text(), self.name )
    def get_output_cmd_name(self):
        if self.is_input:
            return "output_%s" % self.name
        else:
            return self.name
    def get_input_cmd_name(self):
        if self.is_output:
            return "input_%s" % self.name
        else:
            return self.name
    def get_pre_cmd_line( self ):
        text = ''
        if self.is_input:
            text = ''
            cmd_text = "cp '${%s}' '${%s}'" % ( self.get_input_cmd_name(), self.get_output_cmd_name() )
            if not self.required:
                text = """
    #if $%s:
        %s
    #else
        echo ''
    #end if""" % ( self.get_input_cmd_name(), cmd_text )
            else:
                text = cmd_text
        #else:
        #    text = "rm '${%s}'" % ( self.get_output_cmd_name() )
        return text

    def get_post_cmd_line( self ):
        if not self.is_input:
            return "mv '%s.db' '${%s}'" % ( self.name, self.get_output_cmd_name()  )
        return ''


class ParameterContigsDB( ParameterDB ):
    def __init__( self, *args, **kwd ):
        super( ParameterContigsDB, self ).__init__( *args, **kwd )
        self.is_output = True
        self.is_input = not self.name.startswith( 'output' )
        print('is_input', self.name, self.is_input)
        self.is_contigs = True
        self.is_samples = False
        self.basename = 'CONTIGS'
        if self.info_dict.get( 'default', None ) in [ 'SAMPLES.db', ]:
            self.is_contigs = False
            self.is_samples = True
            self.basename = 'SAMPLES'
        #elif self.info_dict.get( 'METAVAR', None ) == 'CONTIGS-DB':
        print('is contigs', self.name, self.is_contigs)
        #self.is_contigs = self.info_dict.get( 'default', None ) == 'CONTIGS.db'
    def get_format( self ):
        if self.is_samples:
            return 'anvio_samples_db'
        if self.is_contigs:
            return "anvio_contigs_db"
        return super( ParameterContigsDB, self ).get_format()
    def to_cmd_line( self ):
        if not ( self.is_contigs or self.is_samples ):
            return super( ParameterContigsDB, self ).to_cmd_line()
        if self.is_input:
            return  "%s '${%s.extra_files_path}/%s.db'\n" % ( self.get_arg_text(), self.get_output_cmd_name(), self.basename )
        else:
            return  "%s '${%s.extra_files_path}/%s.db'\n" % ( self.get_arg_text(), self.get_output_cmd_name(), self.basename )
    def get_pre_cmd_line( self ):
        if not ( self.is_contigs or self.is_samples ):
            return super( ParameterContigsDB, self ).get_pre_cmd_line()
        text = ''
        if self.is_input:
            text = ''
            cmd_text = "cp -R '${%s.extra_files_path}' '${%s.extra_files_path}'" % ( self.get_input_cmd_name(), self.get_output_cmd_name() )
            if not self.required:
                text = """
    #if $%s:
        %s
    #else
        echo ''
    #end if""" % ( self.get_input_cmd_name(), cmd_text )
            else:
                text = cmd_text
        else:
            text = "mkdir '${%s.extra_files_path}'\n" % ( self.get_output_cmd_name() )
        return text

    def get_post_cmd_line( self ):
        if not ( self.is_contigs or self.is_samples ):
            return super( ParameterContigsDB, self ).get_post_cmd_line()
        return ''

class ParameterFASTA( ParameterFILE_PATH ):
    def get_format( self ):
        return "fasta"

class ParameterFASTQ( ParameterFILE_PATH ):
    def get_format( self ):
        return "fastq"

class ParameterGENBANK( ParameterFILE_PATH ):
    def get_format( self ):
        return "genbank"

class ParameterVARIABILITY_TABLE(ParameterFILE_PATH):
    def get_format(self):
        return 'anvio_variability'

class ParameterClassifierFile(ParameterFILE_PATH):
    def get_format(self):
        return 'anvio_classifier'

class ParameterProfileDB( ParameterDB ):
    def __init__( self, *args, **kwd ):
        super( ParameterProfileDB, self ).__init__( *args, **kwd )
        self.is_output = True
        self.is_input = not self.name.startswith( 'output' )
        print('is_input', self.name, self.is_input)
        self.basename='PROFILE'
    def get_format( self ):
        return 'anvio_profile_db'
    def to_cmd_line( self ):
        if self.is_input:
            return  "%s '${%s.extra_files_path}/%s.db'\n" % ( self.get_arg_text(), self.get_output_cmd_name(), self.basename )
        else:
            return  "%s '${%s.extra_files_path}/%s.db'\n" % ( self.get_arg_text(), self.get_output_cmd_name(), self.basename )
    def get_pre_cmd_line( self ):
        text = ''
        if self.is_input:
            text = ''
            cmd_text = "cp -R '${%s.extra_files_path}' '${%s.extra_files_path}'" % ( self.get_input_cmd_name(), self.get_output_cmd_name() )
            if not self.required:
                text = """
    #if $%s:
        %s
    #else
        echo ''
    #end if""" % ( self.get_input_cmd_name(), cmd_text )
            else:
                text = cmd_text
        else:
            text = "mkdir '${%s.extra_files_path}'\n" % ( self.get_output_cmd_name() )
        return text

    def get_post_cmd_line( self ):
        return ''


###
class ParameterPROFILE( ParameterFILE_PATH ):
    def get_format( self ):
        return "anvio_profile_db"
    def to_cmd_line( self ):
        text = ''
        if self.multiple:
            cmd_text = """
            #for $gxy_%s in $%s:
                %s '${gxy_%s.extra_files_path}/PROFILE.db'
            #end for
            """ % ( self.name, self.name, self.get_arg_text(), self.name )
        else:
            cmd_text = "%s '${%s.extra_files_path}/PROFILE.db'" % ( self.get_arg_text(), self.name )
        if not self.multiple:
            text = """
#if $%s:
    %s
#end if\n""" % ( self.name, cmd_text )
        else:
            text = cmd_text
        return text

class ParameterUnknownDB( ParameterFILE_PATH ):
    #TODO: should we copy the inputs to to outputs?
    def __init__( self, *args, **kwd ):
        super( ParameterUnknownDB, self ).__init__( *args, **kwd )
        self.is_output = True
        self.is_input = not self.name.startswith( 'output' )
        #print('is_input', self.name, self.is_input)
        #self.basename='PROFILE'
    def get_format( self ):
        return "anvio_db"
    def get_output_cmd_name(self):
        if self.is_input:
            return "output_%s" % self.name
        else:
            return self.name
    def get_input_cmd_name(self):
        if self.is_output:
            return "input_%s" % self.name
        else:
            return self.name
    def get_base_filename(self, multiple=False):
        if multiple:
            return "${gxy_%s.metadata.anvio_basename}" % self.get_output_cmd_name()
        return "${%s.metadata.anvio_basename}" % self.get_output_cmd_name()
    def to_cmd_line( self ):
        text = ''
        if self.multiple:
            cmd_text = """
            #for $gxy_%s in $%s:
                %s "${gxy_%s.extra_files_path}/%s"
            #end for
            """ % ( self.get_output_cmd_name(), self.get_output_cmd_name(), self.get_arg_text(), self.get_output_cmd_name(), self.get_base_filename(multiple=True) ) #( self.name, self.name, self.get_arg_text(), self.name, self.name )
        else:
            cmd_text = "%s '${%s.extra_files_path}/%s'" % ( self.get_arg_text(), self.get_output_cmd_name(), self.get_base_filename() )
        if not self.multiple:
            text = """
#if $%s:
    %s
#end if\n""" % ( self.get_output_cmd_name(), cmd_text )
        else:
            text = cmd_text
        return text

##
    def get_pre_cmd_line( self ):
        text = ''
        if self.is_input:
            if self.multiple:
                #
                cmd_text = """
                #for $gxy_%s in $%s:
                    cp -R '${gxy_%s.extra_files_path}' '${%s.extra_files_path}'
                #end for
                """ % ( self.get_input_cmd_name(), self.get_input_cmd_name(), self.get_input_cmd_name(), self.get_output_cmd_name() )
                #
            else:
                cmd_text = "cp -R '${%s.extra_files_path}' '${%s.extra_files_path}'" % ( self.get_input_cmd_name(), self.get_output_cmd_name() )
            if not self.required:
                text = """
    #if $%s:
        %s
    #else
        echo ''
    #end if""" % ( self.get_input_cmd_name(), cmd_text )
            else:
                text = cmd_text
        else:
            text = "mkdir '${%s.extra_files_path}'\n" % ( self.get_output_cmd_name() )
        return text

    def get_post_cmd_line( self ):
        return ''


###

class ParameterGenomes( ParameterUnknownDB ):
    def get_format( self ):
        return "anvio_genomes_db"

class ParameterUnknownRUNINFODB( ParameterUnknownDB ):
    def get_base_filename(self, multiple=False):
        return 'RUNINFO.cp'

class ParameterStructureDB(ParameterUnknownDB):
    def get_format( self ):
        return "anvio_structure_db"


class ParameterPANorPROFILEDB( ParameterUnknownDB ):
    #add directory copying
    def get_format( self ):
        return "anvio_profile_db,anvio_pan_db"


class ParameterPANDB( ParameterPANorPROFILEDB ):
    def get_format( self ):
        return "anvio_pan_db"

class ParameterPANDBDIR( ParameterPANDB ):
    def get_base_filename(self, multiple=False):
        return ''


class ParameterDIR_PATH( ParameterFILE_PATH ):
    def get_format( self ):
        return "anvio_composite"
    def to_cmd_line( self ):
        text = ''
        if self.multiple:
            cmd_text = """
            #for $gxy_%s in $%s:
                %s '${gxy_%s.extra_files_path}'
            #end for
            """ % ( self.name, self.name, self.get_arg_text(), self.name )
        else:
            cmd_text = "%s '${%s.extra_files_path}'" % ( self.get_arg_text(), self.name )
        if not self.multiple:
            text = """
#if $%s:
    %s
#end if\n""" % ( self.name, cmd_text )
        else:
            text = cmd_text
        return text

class ParameterOutDIR_PATH(ParameterDIR_PATH):
    def __init__( self, *args, **kwd ):
        super( ParameterOutDIR_PATH, self ).__init__( *args, **kwd )
        self.is_output = True
        self.is_input = False


class ParameterProfileDIR_PATH( ParameterDIR_PATH ):
    def get_format( self ):
        return "anvio_profile_db"

class ParameterHMMProfileDIR_PATH( ParameterDIR_PATH ):
    def get_format( self ):
        return "anvio_hmm_profile"



###

class ParameterINOUTCOMPOSITE_DATA_DIR_PATH( ParameterDB ):
    def __init__( self, *args, **kwd ):
        super( ParameterDB, self ).__init__( *args, **kwd )
        self.is_output = True
        self.is_input = True
    def get_format( self ):
        return "anvio_composite"

    def to_cmd_line( self ):
        if self.is_input:
            return  "%s '${%s.extra_files_path}'\n" % ( self.get_arg_text(), self.get_output_cmd_name() )
        else:
            return  "%s '${%s.extra_files_path}'\n" % ( self.get_arg_text(), self.get_output_cmd_name() )
    def get_pre_cmd_line( self ):
        text = ''
        if self.is_input:
            text = ''
            cmd_text = "cp -R '${%s.extra_files_path}' '${%s.extra_files_path}'" % ( self.get_input_cmd_name(), self.get_output_cmd_name() )
            if not self.required:
                text = """
    #if $%s:
        %s
    #else
        echo ''
    #end if""" % ( self.get_input_cmd_name(), cmd_text )
            else:
                text = cmd_text
        else:
            text = "mkdir '${%s.extra_files_path}'\n" % ( self.get_output_cmd_name() )
        return text

    def get_post_cmd_line( self ):
        return ''

class ParameterCOG_DATA_DIR_PATH( ParameterINOUTCOMPOSITE_DATA_DIR_PATH ):
    def get_format( self ):
        return "anvio_cog_profile"

class ParameterPFAM_DATA_DIR_PATH( ParameterINOUTCOMPOSITE_DATA_DIR_PATH ):
    def get_format( self ):
        return "anvio_pfam_profile"






'''
    def to_cmd_line( self ):
        text = ''
        if self.multiple:
            cmd_text = """
            #for $gxy_%s in $%s:
                %s '${gxy_%s.extra_files_path}'
            #end for
            """ % ( self.name, self.name, self.get_arg_text(), self.name )
        else:
            cmd_text = "%s '${%s.extra_files_path}'" % ( self.get_arg_text(), self.name )
        if not self.multiple:
            text = """
#if $%s:
    %s
#end if\n""" % ( self.name, cmd_text )
        else:
            text = cmd_text
        return text

    def to_cmd_line( self ):
        if self.is_input:
            return  "%s '${%s.extra_files_path}'\n" % ( self.get_arg_text(), self.get_output_cmd_name())
        else:
            return  "%s '${%s.extra_files_path}'\n" % ( self.get_arg_text(), self.get_output_cmd_name())
    def get_pre_cmd_line( self ):
        text = ''
        if self.is_input:
            text = ''
            cmd_text = "cp -R '${%s.extra_files_path}' '${%s.extra_files_path}'" % ( self.get_input_cmd_name(), self.get_output_cmd_name() )
            if not self.required:
                text = """
    #if $%s:
        %s
    #end if""" % ( self.get_input_cmd_name(), cmd_text )
            else:
                text = cmd_text
        else:
            text = "mkdir '${%s.extra_files_path}'\n" % ( self.get_output_cmd_name() )
        return text
'''
#    def get_post_cmd_line( self ):
#        if not ( self.is_contigs or self.is_samples ):
#            return super( ParameterContigsDB, self ).get_post_cmd_line()
#        return ''

####



###

class ParameterRUNINFO_FILE( ParameterDIR_PATH ):
    def to_cmd_line( self ):
        text = ''
        if self.multiple:
            cmd_text = """
            #for $gxy_%s in $%s:
                %s '${gxy_%s.extra_files_path}/RUNINFO.cp'
            #end for
            """ % ( self.name, self.name, self.get_arg_text(), self.name )
        else:
            cmd_text = "%s '${%s.extra_files_path}/RUNINFO.cp'" % ( self.get_arg_text(), self.name )
        if not self.multiple:
            text = """
#if $%s:
    %s
#end if\n""" % ( self.name, cmd_text )
        else:
            text = cmd_text
        return text

class ParamterFILENAME_PREFIX( ParameterDIR_PATH ):
    def get_format( self ):
        return "anvio_composite"
    def to_cmd_line( self ):
        text = ''
        cmd_txt =  "%s '%s'" % ( self.get_arg_text(), self.name )
        if not self.required:
            text = """
#if $str( $%s ):
    %s
#end if\n""" % ( self.name, cmd_txt )
        else:
            text = "%s\n" % cmd_txt
        return text
    def get_pre_cmd_line( self ):
        return 'mkdir ${%s.extra_files_path}' % ( self.name )
    def get_post_cmd_line( self ):
        ##if compgen -G "%s*"
        return '''( cp %s* '${%s.extra_files_path}/' || echo '' )''' % ( self.name, self.name )
        return '''
        if [stat -t "%s*" >/dev/null 2>&1] ;
        then
            cp "%s*" '${%s.extra_files_path}/' ;
        else
            echo ''
        fi
        ''' % ( self.name, self.name, self.name )

class ParameterFILES( ParameterFILE_PATH ):
    def get_format( self ):
        return "data"

class ParameterTABULAR( ParameterFILE_PATH ):
    def get_format( self ):
        return "tabular"

class ParameterNEWICK( ParameterFILE_PATH ):
    def get_format( self ):
        return "newick"

class ParameterSTATE_FILE( ParameterFILE_PATH ):
    def get_format( self ):
        return "anvio_state"

class ParameterINPUT_BAM( ParameterFILE_PATH):
    def get_format( self ):
        return 'bam'
    def get_pre_cmd_line( self ):
        text = ''
        cmd_text = "ln -s '${%s}' '%s.bam' && ln -s '${%s.metadata.bam_index}' '%s.bam.bai'" % ( self.get_input_cmd_name(), self.name, self.get_input_cmd_name(), self.name )
        if not self.required:
            text = """
    #if $%s:
        %s
    #else
        echo ''
    #end if""" % ( self.get_input_cmd_name(), cmd_text )
        else:
            text = cmd_text
        return text
    def to_cmd_line( self ):
        text = ''
        cmd_txt =  "%s '%s.bam'" % ( self.get_arg_text(), self.name )
        if not self.required:
            text = """
#if $%s:
    %s
#end if\n""" % ( self.get_input_cmd_name(), cmd_txt )
        else:
            text = "%s\n" % cmd_txt
        return text

class ParameterINPUT_BAMS( ParameterFILE_PATH):
    def get_format( self ):
        return 'bam'
    def get_pre_cmd_line( self ):
        text = ''
        cmd_text = """
        #for $gxy_i, $input_galaxy_bam in enumerate( $%s ):
        #if $gxy_i != 0:
            &&
        #end if
        ln -s '${input_galaxy_bam}' '${gxy_i}_%s.bam' && ln -s '${input_galaxy_bam.metadata.bam_index}' '${gxy_i}_%s.bam.bai'
        #end for
        """ % ( self.get_input_cmd_name(), self.name, self.name )
        if not self.required:
            text = """
    #if $%s:
        %s
    #else
        echo ''
    #end if""" % ( self.get_input_cmd_name(), cmd_text )
        else:
            text = cmd_text
        return text
    def to_cmd_line( self ):
        text = ''
        cmd_text = """
        #for $gxy_i, $input_galaxy_bam in enumerate( $%s ):
        %s '${gxy_i}_%s.bam'
        #end for
        """ % ( self.get_input_cmd_name(), self.get_arg_text(), self.name )
        if not self.required:
            text = """
#if $%s:
    %s
#end if\n""" % ( self.get_input_cmd_name(), cmd_text )
        else:
            text = "%s\n" % cmd_text
        return text


class ParameterListOrFile( ParameterFILE_PATH ):
    def get_conditional_name( self ):
        return "%s_source" % self.name
    def get_conditional_selector_name( self ):
        return "%s_source_selector" % self.name
    def get_conditional_name_q( self ):
        return quoteattr( self.get_conditional_name() )
    def get_conditional_selector_name_q( self ):
        return quoteattr( self.get_conditional_selector_name() )
    def to_xml_param( self ):
        return """<conditional name=%s>
                      <param name=%s type="select" label="Use a file or list">
                          <option value="file" selected="True">Values from File</option>
                          <option value="list">Values from List</option>
                      </param>
                      <when value="file">
                          <param name=%s type="%s" label=%s format="%s" optional="%s" argument=%s help=%s/>
                      </when>
                      <when value="list">
                          <param name=%s type="text" label=%s value=%s optional="%s" argument=%s help=%s/>
                      </when>
                  </conditional>""" % \
            (
                self.get_conditional_name_q(),
                self.get_conditional_selector_name_q(),
                self.get_name(), 
                self.get_type(),  
                self.get_label(), 
                self.get_format(), 
                self.get_optional(),
                self.get_argument(), 
                self.get_help(),
                self.get_name(), 
                self.get_label(), 
                self.get_default(), 
                self.get_optional(),
                self.get_argument(), 
                self.get_help(),
            )
    def to_cmd_line( self ):
        cmd_txt =  "%s '${%s.%s}'" % ( self.get_arg_text(), self.get_conditional_name(), self.name )
        text = """
#if $str( $%s.%s ) == "file":
    #if $%s.%s:
        %s
    #end if
#else:
    #if $str( $%s.%s ):
        %s
    #end if
#end if
""" % ( self.get_conditional_name(), self.get_conditional_selector_name(),
            self.get_conditional_name(), self.name,
            cmd_txt,
            self.get_conditional_name(), self.name,
            cmd_txt
         )
        return text

DEFAULT_PARAMETER = Parameter

PARAMETER_BY_METAVAR = {
    'PROFILE_DB': ParameterProfileDB,#ParameterPROFILE,#ParameterDB,
    'PAN_DB': ParameterPANDB, #ParameterDB,
    'PAN_OR_PROFILE_DB': ParameterPANorPROFILEDB,#ParameterDB,
    'DB': ParameterUnknownDB,
    'INT': ParameterINT,
    'INTEGER': ParameterINT,
    'FLOAT': ParameterFLOAT,
    'FILE_PATH': ParameterFILE_PATH,
    'FILE': ParameterFILE_PATH,
    'FASTA': ParameterFASTA,
    'LEEWAY_NTs': ParameterINT,
    'WRAP': ParameterINT,
    'NUM_SAMPLES': ParameterINT,
    #'DIR_PATH': ParameterDIR_PATH,
    'DIR_PATH': ParameterProfileDIR_PATH, #should this be profile, or generic anvio, probably generic anvio
    'PERCENT_IDENTITY': ParameterFLOAT,
    'GENE_CALLER_ID': ParameterINT,
    'SMTP_CONFIG_INI': ParameterFILE_PATH,
    'USERS_DATA_DIR': ParameterDIR_PATH,
    'CONTIGS_DB': ParameterContigsDB,#ParameterDB,
    'FILE_NAME': ParameterFILE_PATH,
    'PROFILE': ParameterPROFILE,
    'SAMPLES-ORDER': ParameterTABULAR,
    'E-VALUE': ParameterFLOAT,
    'SAMPLES-INFO': ParameterTABULAR,#ParameterDB,
    'NEWICK': ParameterNEWICK,
    'GENOME_NAMES': ParameterListOrFile,
    'RUNINFO_PATH': ParameterFILE_PATH,
    'ADDITIONAL_LAYERS': ParameterTABULAR,
    'VIEW_DATA': ParameterTABULAR,
    'GENOMES_STORAGE': ParameterGenomes,
    'BINS_INFO': ParameterTABULAR,
    'PATH': ParameterFILE_PATH, #ParameterDIR_PATH, #used in matrix-to-newick
    'NUM_POSITIONS': ParameterINT,
    'CONTIGS_AND_POS': ParameterTABULAR,
    'GENE-CALLS': ParameterTABULAR,
    'ADDITIONAL_VIEW': ParameterTABULAR,
    'DB_FILE_PATH': ParameterContigsDB,#ParameterDB,#fixme should not be contigs, is structure also, should be generic
    'SAMPLES_DB': ParameterContigsDB,#ParameterDB,
    'NUM_CPUS': ParameterNUM_CPUS,
    'FILENAME_PREFIX': ParamterFILENAME_PREFIX,
    'RATIO': ParameterFLOAT,
    'TAB DELIMITED FILE': ParameterTABULAR,
    'INPUT_BAM': ParameterINPUT_BAM,
    'INPUT_BAM(S)': ParameterINPUT_BAMS,
    'RUNINFO_FILE': ParameterRUNINFO_FILE,
    'FILE(S)': ParameterFILES,
    'SINGLE_PROFILE(S)': ParameterPROFILE,
    'TEXT_FILE': ParameterTABULAR,

    'HMM PROFILE PATH': ParameterHMMProfileDIR_PATH,
    'NUM_THREADS': ParameterNUM_CPUS,
    'VARIABILITY_TABLE': ParameterVARIABILITY_TABLE,
    'VARIABILITY_PROFILE': ParameterVARIABILITY_TABLE,
    'STATE_FILE': ParameterSTATE_FILE,
    'DATABASE': ParameterUnknownDB,
    'STRUCTURE_DB': ParameterStructureDB,
    'BAM_FILE': ParameterINPUT_BAM,
    'REPORT_FILE_PATH': ParameterREPORT_FILE_PATH,
    'FLAT_FILE': ParameterFILE_PATH,
    'STATE': ParameterSTATE_FILE,
    'BINS_DATA': ParameterTABULAR,
    'SUMMARY_DICT': ParameterUnknownRUNINFODB,
    'LINKMER_REPORT': ParameterFILE_PATH, #should we add datatype? well output from anvi-report-linkmers is not datatyped due to generic metavar, so can't really
    'DB PATH': ParameterUnknownDB,
    'BAM FILE[S]': ParameterINPUT_BAMS,
    'PAN_DB_DIR': ParameterPANDBDIR,
    'DIRECTORY': ParameterDIR_PATH,
    'FASTA FILE': ParameterFASTA,
    'REPORT FILE': ParameterREPORT_FILE_PATH,
    'GENBANK': ParameterGENBANK,
    'GENBANK_METADATA': ParameterFILE_PATH,
    'OUTPUT_FASTA_TXT': ParameterFILE_PATH,
    'EMAPPER_ANNOTATION_FILE': ParameterFILE_PATH,
    'MATRIX_FILE': ParameterTABULAR,
    'CLASSIFIER_FILE': ParameterClassifierFile,
    'SAAV_FILE': ParameterTABULAR,
    'SCV_FILE': ParameterTABULAR,
    'OUTPUT_FILE': ParameterFILE_PATH,
    'CHECKM TREE': ParameterFILE_PATH,
    'CONFIG_FILE': ParameterFILE_PATH,
    'FASTA_FILE': ParameterFASTA,
    'FASTQ_FILES': ParameterFASTQ,
}

PARAMETER_BY_NAME = {
    'cog-data-dir': ParameterCOG_DATA_DIR_PATH,
    'pfam-data-dir': ParameterPFAM_DATA_DIR_PATH,
    'just-do-it': ParameterBooleanAlwaysTrue,
    'temporary-dir-path': ParameterDiscard,
    'dump-dir': ParameterOutDIR_PATH,
    'full-report': ParameterREPORT_FILE_PATH,
}

#FIXME. make skip just reuse ParameterDiscard
SKIP_PARAMETER_NAMES = ['help', 'temporary-dir-path', 'modeller-executable', 'program', 'log-file', 'gzip-output']
#modeller-executable would allow commandline injection
#program may do same
#help is shown on screen
#temp dirs are handled by system
#log-file, is redundant with output redirect always to log
#gzip will force-add a .gz suffix
SKIP_PARAMETER_NAMES = list(map( lambda x: x.replace( "-", '_' ), SKIP_PARAMETER_NAMES ))



def get_parameter( param_name, arg_short, arg_long, info_dict ):
    if param_name in PARAMETER_BY_NAME:
        param = PARAMETER_BY_NAME[param_name]
    elif 'action' in info_dict and info_dict['action'] not in [ 'help', 'store' ]:
        assert info_dict['action'] == 'store_true'
        param = ParameterBoolean
    else:
        metavar = info_dict.get( 'metavar' )
        print("metavar is dan: %s, %s, %s" % ( param_name, metavar, info_dict ) )
        if metavar is None:
            print("metavar is None: %s, %s" % ( param_name, metavar ) )
        elif metavar not in PARAMETER_BY_METAVAR:
            print("metavar not defined for: %s, %s" % ( param_name, metavar ) )
        param = PARAMETER_BY_METAVAR.get( metavar, DEFAULT_PARAMETER )
    return param( param_name, arg_short, arg_long, info_dict )


import argparse as argparse_original

class FakeArg( argparse_original.ArgumentParser ):
    def __init__( self, *args, **kwd ):
        print('init')
        print('args', args)
        print('kwd', kwd)
        self._blankenberg_args = []
        super( FakeArg, self ).__init__( *args, **kwd )

    def add_argument( self, *args, **kwd ):
        print('add argument')
        print('args', args)
        print('kwd', kwd)
        self._blankenberg_args.append( ( args, kwd ) )
        super( FakeArg, self ).add_argument( *args, **kwd )

    #def add_argument_group( self, *args, **kwd ):
    #    #cheat and return self, no groups!
    #    print 'arg group'
    #    print 'args', args
    #    print 'kwd', kwd
    #    return self

    def blankenberg_params_by_name( self, params ):
        rval = {}#odict()
        for args in self._blankenberg_args:
            name = ''
            for arg in args[0]:
                if arg.startswith( '--' ):
                    name = arg[2:]
                elif arg.startswith( '-'):
                    if not name:
                        name = arg[1]
                else:
                    name = arg
            rval[name] = args[1]
            if 'metavar' not in args[1]:
                print('no metavar', name)
        return rval
    def blankenberg_get_params( self, params ):
        rval = []
        print('blankenberg_get_params params', params)
        for args in self._blankenberg_args:
            name = ''
            arg_short = ''
            arg_long = ''
            for arg in args[0]:
                if arg.startswith( '--' ):
                    name = arg[2:]
                    arg_long = arg
                elif arg.startswith( '-' ):
                    arg_short = arg
                    if not name:
                        name = arg[1:]
                elif not name:
                    name = arg
            param = None
            if name in params:
                print("%s (name) is in params" % (name) )
                param = params[name]
            #if 'metavar' in args[1]:
                #if args[1]['metavar'] in params:
            #        param = params[args[1]['metavar']]
            if param is None:
                if name in PARAMETER_BY_NAME:
                    param = PARAMETER_BY_NAME[name]( name, arg_short, arg_long, args[1] )
            if param is None:
                print("Param is None")
                metavar = args[1].get( 'metavar', None )
                print("asdf metavar",args[1],metavar)
                if metavar and metavar in PARAMETER_BY_METAVAR:
                    param = PARAMETER_BY_METAVAR[metavar]( name, arg_short, arg_long, args[1] )
            if param is None:
                print('no meta_var, using default', name, args[1])
                #param = DEFAULT_PARAMETER( name, arg_short, arg_long, args[1] )
                param = get_parameter( name, arg_short, arg_long, args[1] )

            #print 'before copy', param.name, type(param)
            param = param.copy( name=name, arg_short=arg_short, arg_long=arg_long, info_dict=args[1] )
            #print 'after copy', type(param)
            rval.append(param)
        return rval
    def blankenberg_to_cmd_line( self, params, filename=None ):
        pre_cmd = []
        post_cmd = []
        rval = filename or self.prog
        for param in self.blankenberg_get_params( params ):
            if param.name not in SKIP_PARAMETER_NAMES:
                pre = param.get_pre_cmd_line()
                if pre:
                    pre_cmd.append( pre )
                post = param.get_post_cmd_line()
                if post:
                    post_cmd.append( post )
                cmd = param.to_cmd_line()
                if cmd:
                    rval = "%s\n%s" % ( rval, cmd )
        pre_cmd = "\n && \n".join( pre_cmd )
        post_cmd = "\n && \n".join( post_cmd )
        if pre_cmd:
            rval = "%s\n &&\n %s" % ( pre_cmd, rval )
        rval = "%s\n&> '${GALAXY_ANVIO_LOG}'\n" % (rval)
        if post_cmd:
            rval = "%s\n &&\n %s" % ( rval, post_cmd )
        return rval #+ "\n && \nls -lahR" #Debug with showing directory listing in stdout
    def blankenberg_to_inputs( self, params ):
        rval = []
        for param in self.blankenberg_get_params( params ):
            if param.name not in SKIP_PARAMETER_NAMES and param.is_input:
                inp_xml = param.to_xml_param()
                if inp_xml:
                    rval.append( inp_xml )
        return rval
    def blankenberg_to_outputs( self, params ):
        rval = []
        for param in self.blankenberg_get_params( params ):
            if param.name not in SKIP_PARAMETER_NAMES and param.is_output:
                rval.append( param.to_xml_output() )
        rval.append( GALAXY_ANVIO_LOG_XML )
        return rval



if __name__ == '__main__':
    #unknown_metavar = []
    params = {}
    for param_name, param_tup in []:#list(anvio.D.items()):
        arguments, param_dict = param_tup
        arg_long = ''
        arg_short = ''
        for arg in arguments:
            if arg.startswith( '--' ):
                arg_long = arg
            else:
                arg_short = arg
        
        #print "name",param_name, arg_short, arg_long
        #default = param_dict.get( 'default', '' )
        #metavar = param_dict.get( 'metavar', '' )
        #if metavar and metavar not in PARAMETER_BY_METAVAR.keys() and metavar not in unknown_metavar:
        #    #print 'metavar', metavar
        #    unknown_metavar.append( metavar )
        
        param = get_parameter( param_name, arg_short, arg_long, param_dict )
        params[param_name] = param
        #print param
    outpath = os.path.join( os.curdir, 'output' )
    if not os.path.exists( outpath ):
        os.mkdir( outpath )
    with open(os.path.join(outpath, '.shed.yml'), 'w') as fh:
        fh.write(SHED_YML)

    scripts_outpath = os.path.join( outpath, 'scripts' )
    if not os.path.exists( scripts_outpath ):
        os.mkdir( scripts_outpath )

    xml_count = 0
    for ( read_dir, write_dir ) in [ ( os.path.join( os.curdir, '..', 'bin' ), outpath ), ( os.path.join( os.curdir, '..', 'sandbox' ), scripts_outpath ) ]:
        for ( dirpath, dirnames, filenames ) in os.walk( read_dir ):
            for filename in sorted(filenames):
                arg_groups = []
                if filename in TOOLS_TO_SKIP:
                    #Don't want these tools
                    continue
                if ONLY_DO_TOOLS and filename not in ONLY_DO_TOOLS:
                    print('skipping', filename)
                    continue
                with open( os.path.join( dirpath, filename), 'r' ) as fh:
                    input = fh.read()
                    print(filename, end=' ')
                    if input.startswith( "#!/usr/bin/env python" ):
                        print('python')
                        if "if __name__ == '__main__':" in input:
                            input = input.replace( "if __name__ == '__main__':", "def blankenberg_parsing():", 1)
                            input = input.replace( "argparse.ArgumentParser", "FakeArg")
                            #assert 'parser.parse_args()' in input, "Can't find end! %s" % ( filename )
                            assert 'anvio.get_args(parser)' in input or 'parser.parse_args()' in input or 'parser.parse_known_args()' in input, "Can't find end! %s" % ( filename )
                            inp_list = input.split( '\n' )
                            for i, line in enumerate( inp_list ):
                                if 'parser.parse_args()' in line:
                                    indent = len(line) - len( line.lstrip( ' ' ) )
                                    inp_list[i] = " " * indent + "return parser" #"return parser.parse_args()"
                                if 'anvio.get_args(parser)' in line:
                                    indent = len(line) - len( line.lstrip( ' ' ) )
                                    inp_list[i] = " " * indent + "return parser" #"return parser.parse_args()"
                                if 'parser.parse_known_args()' in line:
                                    indent = len(line) - len( line.lstrip( ' ' ) )
                                    inp_list[i] = " " * indent + "return parser" #"return parser.parse_args()"
                                if 'import ' in line and '"' not in line and line.strip().startswith('import') and '\\' not in line:
                                    indent = len(line) - len( line.lstrip( ' ' ) )
                                    line2 = """%stry:
%s    %s
%sexcept Exception as e:
%s    print ('Failed import', e)
""" % ( " " * indent, " " * indent, line.lstrip( ' ' ), " " * indent, " " * indent )
                                    inp_list[i] = line2
                                if 'add_argument_group' in line:
                                    group_name = line.strip().split()[0]
                                    arg_groups.append( group_name )
                                    #print 'added group', group_name
                                else:
                                    for group_name in arg_groups:
                                        if group_name in line:
                                            line = line.replace( group_name, 'parser' )
                                            inp_list[i] = line

                            output = '\n'.join( inp_list )
                            output = """%s
blankenberg_parameters = blankenberg_parsing()""" % output
                            print(output)
                            exec( output )
                            print('blankenberg_parameters', blankenberg_parameters)
                            print(dir( blankenberg_parameters ))
                            print('desc', blankenberg_parameters.description)
                            #for a in dir( blankenberg_parameters ):
                            #    print '~', a, getattr( blankenberg_parameters, a )
                            #usage = blankenberg_parameters.format_help()
                            #print 'usage', usage
                            print('_blankenberg_args', blankenberg_parameters._blankenberg_args)
                            #print 'by name', blankenberg_parameters.blankenberg_params_by_name( params )
                            print('blankenberg_get_params', blankenberg_parameters.blankenberg_get_params( params ))
                            #print '__version__', __version__
                            #print '__name__', __name__
                            template_dict = {
                                'id': filename.replace( '-', '_'),
                                'name': filename,
                                'version': ANVIO_VERSION,
                                'description': blankenberg_parameters.description,
                                #'macros': None,
                                'version_command': '%s --version' % filename,
                                'requirements': ['<requirement type="package" version="%s">anvio</requirement>' % ANVIO_VERSION ],
                                #'containers': None,
                                'command': blankenberg_parameters.blankenberg_to_cmd_line(params, filename),
                                'inputs': blankenberg_parameters.blankenberg_to_inputs(params),
                                'outputs': blankenberg_parameters.blankenberg_to_outputs(params),
                                #'tests': None,
                                #'tests': { output:'' },
                                'help': blankenberg_parameters.format_help().replace( os.path.basename(__file__), filename),
                                'doi': ['10.7717/peerj.1319'],
                                'bibtex_citations': [galaxy_tool_citation]
                                }
                            print('template_dict', template_dict)
                            tool_xml = Template(TOOL_TEMPLATE).render( **template_dict )
                            print('tool_xml', tool_xml)
                            with open( os.path.join (write_dir, "%s.xml" % filename ), 'w') as out:
                                out.write(tool_xml)
                                xml_count += 1

                            #sys.exit()
                        else:
                            print('no parse!')
                    else:
                        print('not python')
    print("Created %i anvi'o Galaxy tools." % (xml_count))
    '''
                    print filename,
                    line = fh.readline()
                    if line.startswith( "#!/usr/bin/env python" ):
                        print 'python'
                        args = []
                        while True:
                            line = fh.readline()
                            if not line:
                                break
                            line = line.strip()
                            if 'argparse.ArgumentParser' in line:
                                args.append( line )
                                while True:
                                    line = fh.readline()
                                    if not line:
                                        break
                                    line = line.strip()
                                    if 

                            if line.startswith( 'parser' ):
                                args.append( line )
                        print 'args', args
                        assert 'description' in args[0], args[0]
                    else:
                        print line
    '''

        #print 'unknown_metavar', unknown_metavar
        #print 'anvio.D len', len(anvio.D)
        #print 'metavar len', len(unknown_metavar)
    



