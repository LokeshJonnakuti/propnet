from propnet import ureg


def plug_in(symbol_values):
    s = symbol_values['s']
    return {'p': len(s.sites) / s.volume,
            'rho': float(s.density),
            'successful': True}

config = {
    "name": "density",
    "connections": [
        {
            "inputs": [
                "s"
            ],
            "outputs": [
                "p"
            ]
        },
        {
            "inputs": [
                "s"
            ],
            "outputs": [
                "rho"
            ]
        }
    ],
    "categories": [
        "mechanical"
    ],
    "symbol_property_map": {
        "s": "structure",
        "p": "atomic_density",
        "rho": "density"
    },
    "description": "\nModel calculating the atomic density from the corresponding structure object of the material.",
    "references": [],
    "plug_in": plug_in
}
