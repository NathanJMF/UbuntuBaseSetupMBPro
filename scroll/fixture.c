#include "test-events.h"
double libinput_event_pointer_get_scroll_value(struct libinput_event_pointer *e, enum libinput_pointer_axis a) {return e->deltas[a];}
struct libinput_event *libinput_event_pointer_get_base_event(struct libinput_event_pointer *e) {return (void *)e;}
enum libinput_event_type libinput_event_get_type(struct libinput_event *e) {return ((struct libinput_event_pointer *)e)->type;}
