
import bdec.data as dt
from bdec.entry import DecodeLengthError, EntryDataError

class Param:
    def __init__(self, parent_name, child_name):
        self.parent_name = parent_name
        self.child_name = child_name

class Child:
    def __init__(self, name, decoder, passed_params):
        '''A child entry object.

        name -- The name of the child entry.
        decoder -- The decode used to decode the child entry.
        passed_params -- A list of (our_param, child_param) tuples indiating
            what parameters should be passed to and from the child decoder.
        '''
        self.name = name
        self.decoder = decoder
        self.inputs = []
        self.outputs = []
        for our_param, child_param in passed_params:
            names = (our_param.name, child_param.name)
            if child_param.direction == child_param.IN:
                self.inputs.append(names)
            else:
                self.outputs.append(names)

_offset = 0
total = 0

class EntryDecoder:
    def __init__(self, entry, params, is_end_sequenceof, is_value_referenced, is_length_referenced):
        self.entry = entry
        # This list of Child instances will be populated after construction.
        self.children = []

        self._inputs = []
        self._outputs = []
        for param in params:
            if param.direction is param.IN:
                self._inputs.append(param)
            else:
                self._outputs.append(param)
        #if is_end_sequenceof:
            #print '----end----', entry
        self._is_end_sequenceof = is_end_sequenceof
        self._is_value_referenced = is_value_referenced
        self._is_length_referenced = is_length_referenced

    def _decode(self, data, child_context, name):
        """
        Decode the given protocol entry.

        Should return an iterable object for the entry (including all 'child'
        entries) in the same form as Entry.decode.
        """
        raise NotImplementedError()

    def decode(self, data, context, name=None):
        """Return an iterator of (is_starting, name, Entry, data, value) tuples.

        The data returned is_starting==True the data available to be decoded,
        and the data returned when is_starting==False is the decode decoded by
        this entry (not including child entries).

        data -- An instance of bdec.data.Data to decode.
        context -- The context to decode in. Is a lookup of names to integer
           values.
        name -- The name to use for this entry. If None, uses self.name.
        """
        import time
        global _offset
        _offset += 2
        if name is None:
            name = self.entry.name
        #print ' ' * _offset , self.entry, time.clock()
        global total
        total += 1

        # Validate our context
        for param in self._inputs:
            assert param.name in context, "Context to '%s' must include %s!" % (self.entry, param.name)

        try:
            if self.entry.length is not None:
                try:
                    data = data.pop(self.entry.length.evaluate(context))
                except dt.DataError, ex:
                    raise EntryDataError(self.entry, ex)

            # Do the actual decode of this entry (and all child entries).
            length = 0
            for is_starting, name, entry, entry_data, value in self._decode(data, context, name):
                if not is_starting:
                    length += len(entry_data)
                if not is_starting and entry is self.entry:
                    for constraint in self.entry.constraints:
                        constraint.check(self.entry, value, context)
                yield is_starting, name, entry, entry_data, value

            context['should end'] = self._is_end_sequenceof | context.get('should end', False)
            if self._is_value_referenced:
                # The last entry to decode will be 'self', so 'value' will be ours.
                context[self.entry.name] = int(value)
            if self._is_length_referenced:
                context[self.entry.name + ' length'] = length
            if self.entry.length is not None and len(data) != 0:
                raise DecodeLengthError(self.entry, data)
        finally:
            #print ' ' * _offset , self.entry, time.clock()
            _offset -= 2
            pass

    def _decode_child(self, child, data, context):
        """
        Decode a child entry.

        Creates a new context for the child, and after the decode completes,
        will update this entry's context.
        """
        assert isinstance(child, Child), '%s - %s' % (repr(child), child)

        # Create the childs context from our data
        child_context = {}
        for our_name, child_name in child.inputs:
            child_context[child_name] = context[our_name]

        # Do the decode
        for result in child.decoder.decode(data, child_context, child.name):
            yield result

        # Update our context with the output values from the childs context
        for our_name, child_name in child.outputs:
            context[our_name] = child_context[child_name]

