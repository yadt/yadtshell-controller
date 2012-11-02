#! /usr/bin/env python
import yadtshellcontroller

ysc = yadtshellcontroller.Controller()

print 'digraph fsm {'
for event, transitions in ysc.fsm._map.iteritems():
    for src, dst in transitions.iteritems():
        #print '[%s] -> %s -> [%s]' % (src, event, dst)
        print '%s -> %s [label="%s"];' % (src, dst, event)
print '}'
