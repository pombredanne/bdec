
import bdec
import bdec.data as dt
from bdec.decode.entry import EntryDecoder
import bdec.inspect.chooser as chsr

class ChoiceDecoder(EntryDecoder):
    def __init__(self, *args, **kwargs):
        EntryDecoder.__init__(self, *args, **kwargs)
        self._chooser = None

    def _decode(self, data, context, name):
        if self._chooser is None:
            self._chooser = chsr.Chooser([child.decoder.entry for child in self.children])
        # Convert the list of entries to a list of children.
        possibles = []
#        items = list(self._chooser.choose(data))
#        if len(items) > 1:
#            print 'failed to choose: options are', items
#            from bdec.spec.xmlspec import dumps
#            found = set()
#            common = []
#            def recurse(entry):
#                if entry in found:
#                    common.append(entry)
#                    return
#                found.add(entry)
#                for child in entry.children:
#                    recurse(child.entry)
#            for e in items:
#                recurse(e)
#            print 'blah blah'
#            for item in items:
#                print dumps(item, common)
        for entry in self._chooser.choose(data):
            for child in self.children:
                if child.decoder.entry is entry:
                    possibles.append(child)
                    break
            else:
                raise Exception('Failed to find child from possible option %s!' % entry)

        yield (True, name, self.entry, data, None)

        failure_expected = False
        if len(possibles) == 0:
            # None of the items match. In this case we want to choose
            # the 'best' failing option, so we'll examine all of the
            # children.
            possibles = self.children
            failure_expected = True

        was_successful = False
        if len(possibles) == 1:
            best_guess = possibles[0]
        else:
            # We have multiple possibilities. We'll decode them one
            # at a time until one of them succeeds; if none decode,
            # we'll re-raise the exception of the 'best guess'.
            #
            # Note: If we get in here, at best we'll decode the successfully
            # decoding item twice. This can have severe performance
            # implications if choices are embedded within choices (as
            # we get O(N^2) runtime cost).
            #
            # We should possibly emit a warning if we get in here (as it
            # indicates that the specification could be better written).
            best_guess = None
            best_guess_bits = 0
            for child in possibles:
                try:
                    bits_decoded = 0
                    values = []
                    #for is_starting, child_name, entry, entry_data, value in self._decode_child(child, data.copy(), context.copy()):
                    test_context = context.copy()
                    test_data = data.copy()
                    items = list(self._decode_child(child, test_data, test_context))
                    #for is_starting, child_name, entry, entry_data, value in self._decode_child(child, test_data, test_context):
                    #    if not is_starting:
                    #        bits_decoded += len(entry_data)
                    #    values.append((is_starting, child_name, entry, entry_data, value))

                    # We successfully decoded the entry!
                    #best_guess = child
                    context.update(test_context)
                    for item in items:
                        if not item[0]:
                            data.pop(len(item[3]))
                        yield item
                    was_successful = True
                    break
                except bdec.DecodeError:
                    if best_guess is None or bits_decoded > best_guess_bits:
                        best_guess = child
                        best_guess_bits = bits_decoded
        # Decode the best option.
        if not was_successful:
            for is_starting, child_name, entry, data, value in self._decode_child(best_guess, data, context):
                yield is_starting, child_name, entry, data, value

        assert not failure_expected
        yield (False, name, self.entry, dt.Data(), None)
