#include "test-events.h"
#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include <stdio.h>
int main(void) {
    enum libinput_event_type types[] = { LIBINPUT_EVENT_POINTER_SCROLL_FINGER, LIBINPUT_EVENT_POINTER_SCROLL_WHEEL, LIBINPUT_EVENT_POINTER_SCROLL_CONTINUOUS };
    for (int i=0; i<3; i++) {
        struct libinput_event_pointer e={types[i], {20,-10}};
        double factor=i==0 ? 0.15 : 1.0;
        for (int a=0; a<2; a++)
            assert(fabs(libinput_event_pointer_get_scroll_value(&e,a)-e.deltas[a]*factor)<1e-9);
        e.deltas[0]=0;
        assert(libinput_event_pointer_get_scroll_value(&e,0)==0);
    }
    assert(getenv("LD_PRELOAD")==NULL && getenv("MACBOOK_FINGER_SCROLL_PERCENT")==NULL);
    puts("Verified finger, wheel, continuous, both axes, stop events and clean child environment.");
}
