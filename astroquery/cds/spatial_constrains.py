#!/usr/bin/env python
# -*- coding: utf-8 -*

# Licensed under a 3-clause BSD style license - see LICENSE.rst
from astropy import coordinates


class SpatialConstrain:
    def __init__(self, intersect):
        """
        Definition of a SpatialConstrain object

        Parameters
        ----------
        intersect : str
            This parameter can take only three different values:

            - ``overlaps`` (default). The matching data sets are those overlapping the MOC region.
            - ``covers``. The matching data sets are those covering the MOC region.
            - ``encloses``. The matching data sets are those enclosing the MOC region.

        Raises
        ------
        ValueError
            ``intersect`` must have its value in (overlaps, encloses, covers)

        """
        self._intersect = intersect
        if self._intersect == 'encloses':
            self._intersect = 'enclosed'

        self.request_payload = {'intersect': self._intersect}

    @property
    def intersect(self):
        """
        ``intersect`` property

        Returns
        -------
        intersect : str
            ``intersect``

        """
        return self._intersect

    @intersect.setter
    def intersect(self, value):
        """
        ``intersect`` parameter setter property

        Parameters
        ----------
        value : str
            This parameter can take only three different values:

            - ``overlaps`` (default). The matching data sets are those overlapping the MOC region.
            - ``covers``. The matching data sets are those covering the MOC region.
            - ``encloses``. The matching data sets are those enclosing the MOC region.

        Raises
        ------
        ValueError
            ``intersect`` must have its value in (overlaps, encloses, covers)

        """
        if value not in ('overlaps', 'encloses', 'covers'):
            raise ValueError("`intersect` parameter must have a value in ('overlaps', 'encloses', 'covers')")

        self._intersect = value

        if self._intersect == 'encloses':
            self._intersect = 'enclosed'

        self.request_payload.update({'intersect': self._intersect})

    def __repr__(self, *args, **kwargs):
        result = "Spatial constrain having request payload :\n{0}".format(self.request_payload)
        return result


class Cone(SpatialConstrain):

    def __init__(self, center, radius, intersect='overlaps'):
        """
        Definition a cone region

        A cone region is defined by a center position and a radius.
        When sending these parameters to the CDS MOC service, the service
        build a MOC from this region and does the intersection of this newly constructed MOC with the MOCs of the ~20000
        data sets that he already has in memory.
        Selected data sets are those having a not empty MOC intersection (if ``intersect`` is
        equal to overlaps).

        Parameters
        ----------
        center : `~astropy.coordinates.SkyCoord`
            the position of the center of the cone
        radius : `~astropy.coordinates.Angle`
            the radius of the cone
        intersect : str, optional
            default to "overlaps"

        Raises
        ------
        TypeError
            if ``center`` is not of type `~astropy.coordinates.SkyCoord` or
            ``radius`` is not of type `~astropy.coordinates.Angle`

        """

        assert isinstance(center, coordinates.SkyCoord) and isinstance(radius, coordinates.Angle),\
            TypeError('`center` must be of type astropy.coordinates.SkyCoord and/or '
                      '`radius` must be of type astropy.coordinates.Angle')

        SpatialConstrain.__init__(self, intersect)
        self.request_payload.update({
            'DEC': center.dec.to_string(decimal=True),
            'RA': center.ra.to_string(decimal=True),
            'SR': str(radius.value)
        })


class Polygon(SpatialConstrain):

    def __init__(self, vertices, intersect='overlaps'):
        """
        Definition of a polygon region

        A polygon region is defined by a list of vertices.
        When sending a polygon region to the CDS MOC service, the service
        build a MOC from this region and does the intersection of this newly constructed MOC with the MOCs of the ~20000
        data sets that he already has in memory.
        Selected data sets are those having a not empty MOC intersection (if ``intersect`` is
        equal to overlaps).

        Parameters
        ----------
        vertices : [`~astropy.coordinates.SkyCoord`]
            the positions of the polygon vertices
        intersect : str, optional
            default to "overlaps"

        Raises
        ------
        TypeError
            if ``vertices`` is not of type `~astropy.coordinates.SkyCoord`

        AttributeError
            if ``vertices`` does not contain at least 3 positions

        """

        assert isinstance(vertices, coordinates.SkyCoord), \
            TypeError('`vertices` must be of type PolygonSkyRegion')

        SpatialConstrain.__init__(self, intersect)

        # test if the polygon has at least 3 vertices
        if len(vertices.ra) < 3:
            raise AttributeError('`vertices` must have a size >= 3')

        self.request_payload.update({'stc': self._skycoords_to_str(vertices)})

    @staticmethod
    def _skycoords_to_str(vertices):
        """
        Convert vertex positions to a string

        The CDS MOC server needs a polygon expressed in a STC format
        i.e. a str beginning with \'Polygon\' and iterating through
        all the vertices' ra and dec.

        Parameters
        ----------
        vertices : [`~astropy.coordinates.SkyCoord`]
            the positions of the polygon vertices

        Returns
        -------
        polygon_stc : str
            the polygon in stc format

        """

        polygon_stc = "Polygon"
        for i in range(len(vertices.ra)):
            polygon_stc += ' ' + vertices.ra[i].to_string(decimal=True) + \
                           ' ' + vertices.dec[i].to_string(decimal=True)

        return polygon_stc


class Moc(SpatialConstrain):
    def __init__(self, intersect='overlaps'):
        """
        Definition a MOC region

        Parameters
        ----------
        intersect : str, optional

        """

        self.request_payload = {}
        SpatialConstrain.__init__(self, intersect)

    @classmethod
    def from_file(cls, filename, intersect='overlaps'):
        """
        Construct a MOC from a fits file describing the MOC

        Parameters
        ----------
        filename : str
            the filename
        intersect : str, optional
            default to "overlaps"

        Returns
        -------
        moc_constrain : `~astroquery.cds.Moc`
            the MOC region

        """

        assert isinstance(filename, str), TypeError("`filename` must be of type str")

        moc_constrain = cls(intersect=intersect)
        moc_constrain.request_payload.update({'filename': filename})
        return moc_constrain

    @classmethod
    def from_url(cls, url, intersect='overlaps'):
        """
        Construct a MOC from an url leading to a fits file describing the MOC

        Parameters
        ----------
        url : str
            the url where to find the MOC
        intersect : str, optional
            default to "overlaps"

        Returns
        -------
        moc_constrain : `~astroquery.cds.Moc`
            the MOC region

        """

        assert isinstance(url, str), TypeError("`url` must be of type str")

        moc_constrain = cls(intersect=intersect)
        moc_constrain.request_payload.update({'url': url})
        return moc_constrain

    @classmethod
    def from_mocpy_object(cls, mocpy_obj, intersect='overlaps'):
        """
        Construct a MOC from a ``mocpy.MOC`` object

        Parameters
        ----------
        mocpy_obj : ``mocpy.MOC``
            MOC
        intersect : str, optional
            default to "overlaps"

        Returns
        -------
        moc_constrain : `~astroquery.cds.Moc`
            the MOC region

        """

        try:
            from mocpy import MOC
        except ImportError:
            raise ImportError("Could not import mocpy, which is a requirement for the CDS service."
                              "Please see https://github.com/cds-astro/mocpy to install it.")

        assert isinstance(mocpy_obj, MOC), TypeError("`mocpy_obj` must be of type mocpy.MOC")

        # dump the moc in json format in a temp file
        json_moc = mocpy_obj.write(format='json')

        moc_constrain = cls(intersect=intersect)

        moc_constrain.request_payload.update({'moc': str(json_moc)})
        return moc_constrain
