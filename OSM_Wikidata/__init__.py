"""
 This script initializes the plugin, making it known to QGIS.
"""


def classFactory(iface):
    """
    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """

    from .OSM_Wikidata import OSMWikidataDock
    return OSMWikidataDock(iface)
