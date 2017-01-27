# coding=utf-8

from app import db, Doc, Token
from collections import defaultdict
from math import log

try:
    import cpickle as pickle

except ImportError:
    import pickle


NGRAM_FILE = './freqs/ngrams-%s.pickle'

POSTERIOR_FILE = './freqs/posteriors-%s.pickle'

INFORMATIVITY_FILE = './freqs/informativity-%s.pickle'


def get_ngrams(N=3):
    '''Return doc- and corpus-level ngram counts for each word type.

    Counts are based on n-grams of size 1 through N (inclusive).
    Ngrams are stored and returned as a dictionary:

        ngrams = {
            'doc': {
                doc1.id : {
                    0: {
                        ngram1: <count>,
                        ngram2: <count>,
                        ...
                        },
                    ...
                    },
                ...
                },
            'corpus': {
                0: {
                    ngram1: <count>,
                    ngram2: <count>,
                    ...
                    },
                ...
                },
            }
    '''
    try:
        with open(NGRAM_FILE % N, 'rb') as f:
            return pickle.load(f)

    except (IOError, EOFError):
        return _get_ngrams(N)


def _get_ngrams(N):
    print 'Counting ngrams...'

    # create ngrams dictionary
    N_dict = lambda: {i: defaultdict(float) for i in xrange(-1, N)}
    ngrams = {'doc': {}, 'corpus': N_dict()}

    # set corpus-level total (excluding punctuation)
    corpus_total = Token.query.filter_by(punctuation=False).count()
    ngrams['corpus'][-1][''] = corpus_total

    for d in Doc.query.all():
        # add doc-level ngrams dictionary
        ngrams['doc'][d.id] = N_dict()

        # set doc-level total (excluding punctuation)
        doc_total = sum(s.get_token_count() for s in d.sentences)
        ngrams['doc'][d.id][-1][''] = doc_total

        for s in d.sentences:
            # impose sentence-initial marker
            # (Note that there is no need for a sentence-final marker, as </s>
            # will never appear as context, nor will we ever calculate the
            # informativity of </s>.)
            sent = ['<s>'] + [t.word.lower() for t in s.tokens]

            # extract ngram counts
            for i in xrange(len(sent)):
                tok = s.tokens[i-1] if i else None

                for n in range(N):
                    if i >= n:
                        ngram = ' '.join([sent[t] for t in xrange(i-n, i+1)])
                        ngrams['doc'][d.id][n][ngram] += 1  # doc-level
                        ngrams['corpus'][n][ngram] += 1  # corpus-level

                        # store each ngram string
                        try:
                            setattr(tok, 'gram_%s' % str(n + 1), ngram)

                        except AttributeError:
                            continue

        db.session.commit()

    # pickle ngram counts to file
    with open(NGRAM_FILE % N, 'wb') as f:
        pickle.dump(ngrams, f, protocol=pickle.HIGHEST_PROTOCOL)

    return ngrams


def get_posteriors(N=3):
    '''Return doc- and corpus-level posterior probabilities of each word type.

    Posteriors are based on n-grams of size 1 through N (inclusive).
    Posteriors are stored and returned as a dictionary:

        posteriors = {
            'doc': {
                doc1.id : {
                    0: {
                        tok1.id: <posterior>,
                        tok2.id: <posterior>,
                        ...
                        },
                    ...
                    },
                ...
                },
            'corpus': {
                0: {
                    tok1.id: <posterior>,
                    tok2.id: <posterior>,
                    ...
                    },
                ...
                },
            }
    '''
    try:
        with open(POSTERIOR_FILE % N, 'rb') as f1:

            with open(INFORMATIVITY_FILE % N, 'rb') as f2:
                assert f2

            return pickle.load(f1)

    except (IOError, EOFError, AssertionError):
        return _get_posteriors(N)


def _get_posteriors(N):
    # load ngrams dictionary
    ngrams = get_ngrams(N)

    print 'Calculating posteriors...'

    # create posteriors dictionary
    N_dict = lambda: {i: {} for i in xrange(N)}
    posteriors = {'doc': {}, 'corpus': N_dict()}

    # create base informativity dictionary
    S_dict = lambda: defaultdict(lambda: {i: set() for i in xrange(1, N)})
    informativity = {'doc': {}, 'corpus': S_dict()}

    for d in Doc.query.all():
        # add doc-level posteriors and informativity dictionaries
        posteriors['doc'][d.id] = N_dict()
        informativity['doc'][d.id] = S_dict()

        for s in d.sentences:
            # impose sentence-initial marker
            # (Note that there is no need for a sentence-final marker, as </s>
            # will never appear as context, nor will we ever calculate the
            # informativity of </s>.)
            sent = ['<s>'] + [t.word.lower() for t in s.tokens]

            # extract posteriors
            for i in xrange(1, len(sent)):
                tok = s.tokens[i-1]

                if not tok.punctuation:
                    for n in xrange(N):
                        if i >= n:
                            NUM = ' '.join([sent[t] for t in xrange(i-n, i+1)])
                            DEN = ' '.join([sent[t] for t in xrange(i-n, i)])

                            # doc-level posterior
                            d_num = ngrams['doc'][d.id][n][NUM]
                            d_den = ngrams['doc'][d.id][n-1][DEN]
                            d_posterior = d_num / d_den
                            posteriors['doc'][d.id][n][tok.id] = d_posterior

                            # corpus-level posterior
                            c_num = ngrams['corpus'][n][NUM]
                            c_den = ngrams['corpus'][n-1][DEN]
                            c_posterior = c_num / c_den
                            posteriors['corpus'][n][tok.id] = c_posterior

                            # collect values to calculate informativity
                            try:
                                sigma = sent[i]

                                # doc-level
                                informativity['doc'][d.id][sigma][n].add(
                                    (NUM, d_num * -log(d_posterior, 2)))

                                # corpus-level
                                informativity['corpus'][sigma][n].add(
                                    (NUM, c_num * -log(c_posterior, 2)))

                            except KeyError:
                                pass

    # calculate informativity
    _get_informativity(informativity, ngrams, N)

    # pickle posteriors to file
    with open(POSTERIOR_FILE % N, 'wb') as f:
        pickle.dump(posteriors, f, protocol=pickle.HIGHEST_PROTOCOL)

    return posteriors


def get_informativity(N=3):
    '''Return doc- and corpus-level informativity of each word type.

    Informativity is based on n-grams of size 1 through N (inclusive).
    Informativity results are stored and returned as a dictionary:

        informativity = {
            'doc': {
                doc1.id : {
                    sigma1: {
                        1: <bigram_informativity>,
                        2: <trigram_informativity>,
                        ...
                        },
                    ...
                    },
                ...
                },
            'corpus': {
                sigma1: {
                    1: <bigram_informativity>,
                    2: <trigram_informativity>,
                    ...
                    },
                ...
                },
            }
    '''
    try:
        with open(INFORMATIVITY_FILE % N, 'rb') as f:
            return pickle.load(f)

    except (IOError, EOFError):
        # informativity is calculated at the same time as posteriors
        get_posteriors(N)

        return get_informativity(N)


def _get_informativity(informativity, ngrams, N):
    print 'Calculating informativity...'

    # calculate doc-level informativity
    for doc_id, sig_dict in informativity['doc'].iteritems():
        sig_dict = dict(sig_dict)  # convert sigma defaultdict to dict

        for sigma, sizes in sig_dict.iteritems():
            sigma_count = ngrams['doc'][doc_id][0][sigma]

            for n, values in sizes.iteritems():
                sizes[n] = sum([v for _, v in values]) / sigma_count

        informativity['doc'][doc_id] = sig_dict

    # calculate corpus-level informativity
    for sigma, sizes in informativity['corpus'].iteritems():
        sigma_count = ngrams['corpus'][0][sigma]

        for n, values in sizes.iteritems():
            sizes[n] = sum([v for _, v in values]) / sigma_count

    # convert sigma defaultdict to dict
    informativity['corpus'] = dict(informativity['corpus'])

    # pickle posteriors to file
    with open(INFORMATIVITY_FILE % N, 'wb') as f:
        pickle.dump(informativity, f, protocol=pickle.HIGHEST_PROTOCOL)


def set_data(N=3):
    '''Write frequency, posterior, and informativity data to database.'''
    ngrams = get_ngrams()
    P = get_posteriors()
    I = get_informativity()

    for d in Doc.query.all():
        words = [t for s in d.sentences for t in s.tokens if not t.punctuation]

        for t in words:
            w = t.word.lower()

            # set frequencies
            t.doc_freq = ngrams['doc'][d.id][0][w]
            t.corpus_freq = ngrams['corpus'][0][w]

            # set posteriors
            for num in xrange(0, N):
                n = str(num + 1)
                setattr(t, 'doc_posterior_%s' % n, P['doc'][d.id][num].get(t.id, 0))  # noqa
                setattr(t, 'corpus_posterior_%s' % n, P['corpus'][num].get(t.id, 0))  # noqa

            # set informativity
            for num in xrange(1, N):
                n = str(num + 1)
                setattr(t, 'doc_inform_%s' % n, I['doc'][d.id][w][num])
                setattr(t, 'corpus_inform_%s' % n, I['corpus'][w][num])

        db.session.commit()


if __name__ == '__main__':
    set_data()
