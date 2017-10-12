# -*- coding: utf-8
# pylint: disable=line-too-long
"""Module to deal with HDF5 files"""

import h5py
import time
import numpy as np

import anvio
import anvio.db as db
import anvio.tables as t
import anvio.utils as utils
import anvio.terminal as terminal
import anvio.constants as constants
import anvio.filesnpaths as filesnpaths

from anvio.errors import HDF5Error


__author__ = "A. Murat Eren"
__copyright__ = "Copyright 2015, The anvio Project"
__credits__ = []
__license__ = "GPL 3.0"
__maintainer__ = "A. Murat Eren"
__email__ = "a.murat.eren@gmail.com"


run = terminal.Run()
progress = terminal.Progress()
pp = terminal.pretty_print

class HDF5_IO(object):
    def __init__(self, file_path, unique_hash, create_new=False, open_in_append_mode=False, ignore_hash=False, run=run, progress=progress, quiet=False):
        self.run = run
        self.progress = progress

        self.file_path = file_path

        if open_in_append_mode and not create_new:
            raise HDF5Error("The 'open_in_append_mode' flag can only be used along with the flag 'create_new'.")

        if create_new:
            if ignore_hash:
                raise HDF5Error("When creating (or appending to) a database, you can't use the 'ignore_hash'\
                                  flag.")

            if not unique_hash:
                raise HDF5Error("When creating (or appending to) a database, the 'unique_hash' cannot be None.")

            self.fp = h5py.File(self.file_path, 'a' if open_in_append_mode else 'w')
            self.fp.attrs['hash'] = unique_hash
            self.fp.attrs['version'] = self.version
        else:
            filesnpaths.is_file_exists(self.file_path)
            self.fp = h5py.File(self.file_path, 'r')

            G = lambda x: self.fp.attrs[x].decode('utf-8') if isinstance(self.fp.attrs[x], bytes) else self.fp.attrs[x]
            fp_version = G('version')
            fp_hash = G('hash')

            if fp_version != self.version:
                raise HDF5Error("The data file for %s ('%s') is at version '%s', however, your client is at\
                                 version '%s'. This is bad news, because your version of anvi'o can't work with\
                                 this file. You can regenerate the data file using the current version of anvi'o,\
                                 or look around to see whether there is an upgrade script is available (a good start\
                                 would be to type 'anvi-script-upgrade-' and then click TAB key twice). Otherwise you\
                                 may want to consider sending an e-mail to the anvi'o developers to find out what's up.\
                                 We heard that they love them some e-mails." % (self.db_type, self.file_path, self.fp.attrs['version'], self.version))

            if not ignore_hash and fp_hash != unique_hash:
                raise HDF5Error("The database at '%s' does not seem to be compatible with the client :/\
                                  (i.e., the hash values do not match)." % self.file_path)

            self.unique_hash = fp_hash


    def add_integer_list(self, path, l, data_type='uint16'):
        """Add an array into the the HDF5 file.

            >>> h = HDF5_IO('test.h5')
            >>> l = [1, 2, 3, 4, 5]
            >>> h.add_integer_list('/split_1/sample_x', l)
            >>> h.close()
        """

        new_data_obj = self.fp.create_dataset(path, (len(l),), dtype=np.dtype(data_type), compression="gzip")
        new_data_obj[...] = np.array(l)


    def get_integer_list(self, path):
        l = self.fp[path]
        return l.value


    def path_exists(self, path):
        return path in self.fp


    def close(self):
        self.fp.close()


class AuxiliaryDataForSplitCoverages(object):
    def __init__(self, file_path, db_hash, split_names_of_interest=None, create_new=False, ignore_hash=False, run=run, progress=progress, quiet=False):
        self.db_type = 'auxiliary data for coverages'
        self.db_hash = db_hash
        self.version = anvio.__auxiliary_data_version__
        self.file_path = file_path
        self.quiet = quiet

        self.db = db.DB(self.file_path, self.version, new_database=create_new)

        if create_new:
            self.create_tables()

        # set sample and split names in the auxiliary data file
        self.sample_names_in_db = set(self.db.get_single_column_from_table('sample_name')) if not create_new else set([])
        self.split_names_in_db = set(self.db.get_single_column_from_table('split_name')) if not create_new else list()
        self.split_names_of_interest = set(split_names_of_interest) if split_names_of_interest else None

        self.split_names = self.split_names_of_interest or self.split_names_in_db


    def create_tables(self):
        self.db.set_meta_value('db_type', self.db_type)
        self.db.set_meta_value('contigs_db_hash', self.db_hash)
        self.db.set_meta_value('creation_date', time.time())
        self.db.create_table(t.split_coverages_table_name, t.split_coverages_table_structure, t.split_coverages_table_types)

    def append(self, split_name, sample_id, coverage_list):
        coverage_list_blob = db.binary(np.array(coverage_list, dtype=np.uint16))
        self.db._exec('''INSERT INTO %s VALUES (?,?,?)''' % t.split_coverages_table_name, (split_name, sample_id, coverage_list_blob, ))

    def check_sample_names(self, sample_names, split_name=None):
        if sample_names:
            if not isinstance(sample_names, set):
                raise HDF5Error('The type of sample names must be a "set".')

        if sample_names:
            for sample_name in sample_names:
                missing_samples = [sample_name for sample_name in sample_names if sample_name not in self.sample_names_in_db]
                if len(missing_samples):
                    raise HDF5Error("Some sample names you requested are missing from the auxiliary data file. Here\
                                        they are: '%s'" % (', '.join(missing_samples)))
            return sample_name

        return self.sample_names_in_db


    def get_all(self, sample_names=[]):
        self.progress.new('Recovering split coverages')
        self.progress.update('...')
        sample_names = self.check_sample_names(sample_names)

        split_coverages = {}
        num_splits, counter = len(self.split_names), 1
        for i in range(0, num_splits):
            if num_splits > 100 and counter % 100 == 0:
                self.progress.update('%d of %d splits ...' % (counter, num_splits))

            split_name = self.split_names[i]
            split_coverages[split_name] = {}
            for sample_name in self.sample_names_in_db:
                split_coverages[split_name][sample_name] = self.get_integer_list('/data/coverages/%s/%s' % (split_name, sample_name))

            counter += 1

        self.progress.end()

        return split_coverages


    def get(self, split_name, sample_names=[]):
        self.is_known_split(split_name)

        sample_names = self.check_sample_names(sample_names)

        d = {}
        for sample_name in sample_names:
            d[sample_name] = self.get_integer_list('/data/coverages/%s/%s' % (split_name, sample_name))

        return d

    def close(self):
        self.db.disconnect()


class AuxiliaryDataForNtPositions(HDF5_IO):
    """A class to handle HDF5 operations to store and access split coverages"""
    def __init__(self, file_path, db_hash, create_new = False, run=run, progress=progress, quiet = False):
        self.db_type = 'auxiliary data for nt positions'
        self.version = anvio.__auxiliary_data_version__

        HDF5_IO.__init__(self, file_path, db_hash, create_new = create_new)

        self.quiet = quiet


    def is_known_contig(self, contig_name):
        path = '/data/nt_position_info/%s' % contig_name
        return self.path_exists(path)


    def append(self, contig_name, position_info_list):
        self.add_integer_list('/data/nt_position_info/%s' % contig_name, position_info_list, data_type = 'uint8')


    def get(self, contig_name):
        if not self.is_known_contig(contig_name):
            return []

        return self.get_integer_list('/data/nt_position_info/%s' % contig_name)


class GenomesDataStorage(HDF5_IO):
    """A class to handle HDF5 operations to store and access sequnces in pan genome analyses.

       An example:

           >>> x = a.GenomesDataStorage('test.h5', 'unique_hash', create_new=True)
           >>> x.add_gene_call_data('genome_name', int_gene_caller_id,
                                    sequence = 'IMLQWIVIIYFLVINLVLFSMMGYDKKQAKRGNWRIPERRLLTIGLVGGGLGGLMGQKKFHHKTQKPVFALCYSIGVIAMISCIYLTFK',
                                    dna_sequence = 'AATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGTCGATCG(...)',
                                    partial = 0,
                                    functions = [('PFAM', 'PFAM FUNC_1'), ('TIGRFAM', 'sik')],
                                    taxonomy_dict = {'t_phylum': 'phy', 't_class': 'clas', 't_order': 'ord', 't_family': None, 't_genus': 'genus', 't_species': 'sp'})
           >>> x.close()
           >>> x = a.GenomesDataStorage('test.h5', 'unique_hash')
           >>> x.get_gene_sequence('genome_name', int_gene_caller_id)
           IMLQWIVIIYFLVINLVLFSMMGYDKKQAKRGNWRIPERRLLTIGLVGGGLGGLMGQKKFHHKTQKPVFALCYSIGVIAMISCIYLTFK
    """

    def __init__(self, file_path, db_hash, genome_names_to_focus=None, create_new=False, ignore_hash=False, run=run, progress=progress, quiet=False):
        self.db_type = 'genomes data storage'
        self.version = anvio.__genomes_storage_version__
        self.genome_names_to_focus = genome_names_to_focus

        HDF5_IO.__init__(self, file_path, db_hash, create_new = create_new, ignore_hash = ignore_hash)

        self.run = run
        self.progress = progress
        self.quiet = quiet

        self.essential_genome_info = constants.essential_genome_info + ['genome_hash', 'external_genome']

        self.D = lambda genome_name: self.fp['/data/genomes/%s' % genome_name]
        self.G = lambda gene_callers_id, genome_data: genome_data['%d' % gene_callers_id]

        if not create_new:
            self.genome_names = self.get_genome_names_in_db()

            if self.genome_names_to_focus:
                genome_names_to_focus_missing_from_db = [g for g in self.genome_names_to_focus if g not in self.genome_names]

                # make sure the user knows what they're doing
                if genome_names_to_focus_missing_from_db:
                    raise HDF5Error("%d of %d genome names you wanted to focus are missing from the genomes sotrage.\
                                     Although this may not be a show-stopper, anvi'o likes to be explicit, so here we\
                                     are. Not going anywhere until you fix this. For instance this is one of the missing\
                                     genome names: '%s', and this is one random genome name from the database: '%s'" % \
                                             (len(genome_names_to_focus_missing_from_db), len(self.genome_names_to_focus),\
                                             genome_names_to_focus_missing_from_db[0], list(self.genomes.keys())[0]))

                self.genome_names = self.genome_names_to_focus

            self.num_genomes = len(self.genome_names)
            self.functions_are_available = self.fp.attrs['functions_are_available']

            self.run.info('Genomes storage', 'Initialized (storage hash: %s)' % (self.unique_hash))
            self.run.info('Num genomes in storage', len(self.get_genome_names_in_db()))
            self.run.info('Num genomes will be used', len(self.genome_names), mc='green')


    def is_known_genome(self, genome_name, throw_exception=True):
        if not self.path_exists('/info/genomes/%s' % genome_name):
            if throw_exception:
                raise HDF5Error('The database at "%s" does not know anything about "%s" :(' % (self.file_path, genome_name))
            else:
                return False


    def is_known_gene_call(self, genome_name, gene_caller_id):
        if not self.path_exists('/data/genomes/%s/%d' % (genome_name, gene_caller_id)):
            raise HDF5Error('The genome "%s" does not know anything about the gene caller id "%d" :(' % (genome_name, gene_caller_id))


    def add_gene_call_data(self, genome_name, gene_caller_id, aa_sequence, dna_sequence, partial=0, functions = [], taxonomy_dict = None):
        """Add a gene call in a genome into the database"""
        self.fp['/data/genomes/%s/%d/aa_sequence' % (genome_name, gene_caller_id)] = aa_sequence
        self.fp['/data/genomes/%s/%d/dna_sequence' % (genome_name, gene_caller_id)] = dna_sequence
        self.fp['/data/genomes/%s/%d/length' % (genome_name, gene_caller_id)] = len(aa_sequence)
        self.fp['/data/genomes/%s/%d/partial' % (genome_name, gene_caller_id)] = partial

        if taxonomy_dict:
            for t_level in t.taxon_names_table_structure[1:]:
                self.fp['/data/genomes/%s/%d/taxonomy/%s' % (genome_name, int(gene_caller_id), t_level)] = taxonomy_dict[t_level] or ''

        for source, function in functions:
            self.fp['/data/genomes/%s/%d/functions/%s' % (genome_name, gene_caller_id, source)] = function


    def is_partial_gene_call(self, genome_name, gene_caller_id):
        self.is_known_genome(genome_name)
        self.is_known_gene_call(genome_name, gene_caller_id)

        d = self.fp['/data/genomes/%s/%d/partial' % (genome_name, gene_caller_id)]

        return d.value


    def get_gene_sequence(self, genome_name, gene_caller_id, report_DNA_sequences=False):
        """Returns gene amino acid sequence unless `report_DNA_sequences` is True."""

        self.is_known_genome(genome_name)
        self.is_known_gene_call(genome_name, gene_caller_id)

        if report_DNA_sequences:
            d = self.fp['/data/genomes/%s/%d/dna_sequence' % (genome_name, gene_caller_id)]
        else:
            d = self.fp['/data/genomes/%s/%d/aa_sequence' % (genome_name, gene_caller_id)]

        return d.value


    def get_gene_functions(self, genome_name, gene_caller_id):
        if not self.functions_are_available:
            raise HDF5Error("Functions are not available for this genome storage, and you are calling GenomesStorage::get_gene_functions\
                              when you really shouldn't :/")

        functions = {}

        if 'functions' not in self.fp['/data/genomes/%s/%d' % (genome_name, gene_caller_id)]:
            # no sources provided any annotation for this poor gene
            return functions

        d = self.fp['/data/genomes/%s/%d/functions' % (genome_name, gene_caller_id)]
        for source in d:
           functions[source] = d[source].value

        return functions


    def add_genome(self, genome_name, info_dict):
        if self.is_known_genome(genome_name, throw_exception=False):
            raise HDF5Error("Genome '%s' is already in this data storage :/" % genome_name)

        for key in self.essential_genome_info:
            # the following line will add a -1 for any `key` that has the value of `None`. the reason
            # we added this was to be able to work with contigs databases without any hmm hits for SCGs
            # which is covered in https://github.com/merenlab/anvio/issues/573
            self.fp['/info/genomes/%s/%s' % (genome_name, key)] = info_dict[key] if info_dict[key] is not None else -1


    def get_storage_hash(self):
        return self.fp.attrs['hash']


    def get_genome_names_in_db(self):
        return [d for d in self.fp['/info/genomes']]


    def get_genomes_dict(self):
        genomes_dict = {}

        for genome_name in self.genome_names:
            genomes_dict[genome_name] = {}
            genomes_dict[genome_name]['name'] = genome_name

            # add every key-value pair we know of in to the dict:
            for key in self.fp['/info/genomes/%s' % genome_name]:
                genomes_dict[genome_name][key] = self.fp['/info/genomes/%s/%s' % (genome_name, key)].value

            # add in AA sequence lengths dict for each gene caller uisng '/data/genomes':
            genomes_dict[genome_name]['gene_lengths'] = {}
            genome_data = self.D(genome_name)
            for gene_caller_id in genome_data:
                genomes_dict[genome_name]['gene_lengths'][int(gene_caller_id)] = genome_data[gene_caller_id]['length'].value

        return genomes_dict


    def gen_combined_aa_sequences_FASTA(self, output_file_path, exclude_partial_gene_calls=False):
        self.run.info('Exclude partial gene calls', exclude_partial_gene_calls, nl_after=1)

        genomes = self.get_genomes_dict()

        total_num_aa_sequences = 0
        total_num_excluded_aa_sequences = 0

        output_file = open(output_file_path, 'w')

        for genome_name in genomes:
            self.progress.new('Storing aa sequences')
            self.progress.update('%s ...' % genome_name)

            genome_data = self.D(genome_name)
            gene_caller_ids = sorted([int(i[0]) for i in list(genome_data.items())])

            for gene_caller_id in gene_caller_ids:
                partial = self.G(gene_caller_id, genome_data)['partial'].value

                if exclude_partial_gene_calls and partial:
                    total_num_excluded_aa_sequences += 1
                    continue

                aa_sequence = self.G(gene_caller_id, genome_data)['aa_sequence'].value

                output_file.write('>%s_%d\n' % (genomes[genome_name]['genome_hash'], int(gene_caller_id)))
                output_file.write('%s\n' % aa_sequence)

                total_num_aa_sequences += 1

            self.progress.end()

        output_file.close()

        self.progress.new('Uniquing the output FASTA file')
        self.progress.update('...')
        unique_aas_FASTA_path, unique_aas_names_file_path, unique_aas_names_dict = utils.unique_FASTA_file(output_file_path, store_frequencies_in_deflines=False)
        self.progress.end()

        self.run.info('Unique AA sequences FASTA', output_file_path)
        self.run.info('Num AA sequences reported', '%s' % pp(total_num_aa_sequences), nl_before=1)
        self.run.info('Num excluded gene calls', '%s' % pp(total_num_excluded_aa_sequences))

        return unique_aas_FASTA_path, unique_aas_names_dict
