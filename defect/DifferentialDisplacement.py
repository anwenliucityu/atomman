# coding: utf-8

# http://www.numpy.org/
import numpy as np

# https://matplotlib.org/
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import cm
from matplotlib.pyplot import MultipleLocator

# atomman imports
from ..tools import axes_check
from .. import Box, NeighborList

class DifferentialDisplacement():
    def __init__(self, system_0, system_1, neighbors=None, cutoff=None, reference=1):
        """
        Class initializer.  Calls solve if either neighbors or cutoff are given.
        
        Parameters
        ----------
        system_0 : atomman.system
            The base/reference system to use.
        system_1 : atomman.system
            The defect/current system to use.
        neighbors : atomman.NeighborList, optional
            The neighbor list to use.  
        cutoff : float, optional
            Cutoff distance for computing a neighbor list. If reference = 0, then system_0
            will be used to generate the list. If reference = 1, then system_1 will be
            used to generate the list.
        reference : int, optional
            Indicates which of the two systems should be used for the plotting
            reference: 0 or 1. If 0, then system_0's atomic positions will be
            used for the calculation and neighbors should be for system_0.  If
            1 (default), then system_1's atomic positions will be used
            for the calculation and neighbors should be for system_1.   
        """
        
        if neighbors is not None or cutoff is not None:
            self.solve(system_0, system_1, neighbors=neighbors, cutoff=cutoff, reference=reference)
        else:
            assert system_0.natoms == system_1.natoms
            
            self.__system_0 = system_0
            self.__system_1 = system_1
            self.reference = reference
            self.__neighbors = None
            self.__ddvectors = None
            self.__arrowcenters = None
            self.__arrowuvectors = None
    
    @property
    def reference(self):
        """int : Indicates which system (0 or 1) is used as the reference."""
        return self.__reference

    @reference.setter
    def reference(self, value):
        assert value == 0 or value == 1, 'reference must be 0 or 1'
        self.__reference = value    
    
    @property
    def system0(self):
        """atomman.System : The defect-free base system."""
        return self.__system0
    
    @property
    def system1(self):
        """atomman.System : The defect containing system."""
        return self.__system1
    
    @property
    def neighbors(self):
        """atomman.NeighborList : The list of neighbors identified for the reference system."""
        return self.__neighbors
    
    @property
    def ddvectors(self):
        """numpy.array or None : The computed differential displacement vectors."""
        return self.__ddvectors
    
    @property
    def arrowcenters(self):
        """numpy.array or None : The identified center positions for the ddvectors."""
        return self.__arrowcenters
    
    @property
    def arrowuvectors(self):
        """numpy.array or None : The unit vectors between all pairs of atoms for which the ddvectors have been computed."""
        return self.__arrowuvectors
    
    def solve(self, system0=None, system1=None, neighbors=None, cutoff=None, reference=None):
        """
        Solves the differential displacement vectors.
        
        Parameters
        ----------
        system0 : atomman.system
            The base/reference system to use.
        system1 : atomman.system
            The defect/current system to use.
        neighbors : atomman.NeighborList, optional
            The neighbor list to use.  
        cutoff : float, optional
            Cutoff distance for computing a neighbor list. If reference = 0, then system_0
            will be used to generate the list. If reference = 1, then system_1 will be
            used to generate the list.
        reference : int, optional
            Indicates which of the two systems should be used for the plotting reference: 0 or 1.
            If 0 (default), then system0's atomic positions will be used for the calculation and
            neighbors should be for system0.  If 1, then system1's atomic positions will be used
            for the calculation and neighbors should be for system1.   
        """
        # Handle parameters
        if system0 is not None:
            self.__system0 = system0
        else:
            system0 = self.system0
        if system1 is not None:
            self.__system1 = system1
        else:
            system1 = self.system1
        assert system0.natoms == system1.natoms
        
        if reference is None:
            reference = self.reference
        else:
            self.reference = reference
        if reference == 0:
            refsystem = system0
        else:
            refsystem = system1
        
        if neighbors is None:
            if cutoff is not None:
                self.__neighbors = neighbors = refsystem.neighborlist(cutoff=cutoff)
            else:
                if self.neighbors is not None:
                    neighbors = self.neighbors
                else:
                    raise ValueError('Either neighbors or cutoff must be given')
        else:
            self.__neighbors = neighbors
        
        all_ddvectors = []
        all_arrowcenters = []
        all_arrowuvectors = []
        
        # Loop over all atoms i in ref system
        for i in np.arange(refsystem.natoms):
            neighs = neighbors[i]
            if len(neighs) == 0:
                continue
            
            # Compute distance vectors between atom i and its neighbors for both systems
            dvectors0 = system0.dvect(int(i), neighs)
            dvectors1 = system1.dvect(int(i), neighs)
            if dvectors0.shape == (3,):
                dvectors0.shape = (1,3)
                dvectors1.shape = (1,3)

            # Compute differential displacement vectors
            ddvectors = dvectors1 - dvectors0

            # Compite center points and direction vectors
            if reference == 0:
                arrowcenters = system0.atoms.pos[i] + dvectors0 / 2
                arrowuvectors = dvectors0 / np.linalg.norm(dvectors0, axis=1)[:,np.newaxis]    
            else:    
                arrowcenters = system1.atoms.pos[i] + dvectors1 / 2
                arrowuvectors = dvectors1 / np.linalg.norm(dvectors1, axis=1)[:,np.newaxis]
                
            # Append calculation values to associated lists            
            all_ddvectors.append(ddvectors)
            all_arrowcenters.append(arrowcenters)
            all_arrowuvectors.append(arrowuvectors)
        
        # Save computed values to object properties 
        self.__ddvectors = np.concatenate(all_ddvectors)
        self.__arrowcenters = np.concatenate(all_arrowcenters)
        self.__arrowuvectors = np.concatenate(all_arrowuvectors)
        
    def plot(self, system, component, ddmax, plotxaxis='x', plotyaxis='y',
             xlim=None, ylim=None, zlim=None,
             arrowscale=1, arrowwidth=0.005,  use0z=False,
             atomcolor=None, atomcmap=None, atomsize=0.5, figsize=10,
             matplotlib_axes=None, cmap='bwr', xbins=200, ybins=200, scale=1, nye_index=[0,0],alat=4.05,calculation=True):

        r"""
        Creates a matplotlib figure of a differential displacement map.  Atom
        positions are represented as circles, while the selected components of the
        differential displacement vectors are plotted as arrows.
        
        Parameters
        ----------
        component : str or array-like object
            Indicates the component(s) of the differential displacement to plot.
            Values of 'x', 'y', or 'z' will plot the component along that
            Cartesian direction.  A value of 'projection' will plot the
            differential displacement vectors as projected onto the plotting
            plane, thereby showing the two components perpendicular to the line
            direction.  If a 3D vector is given, then the component parallel to
            that direction will be used.
        ddmax : float or None
            The maximum differential displacement value allowed. Values will be
            kept between +-ddmax by wrapping values with larger absolute values
            around by adding/subtracting 2*ddmax. Typically, this is set to be
            \|b\|/2, but can be defect-specific. For instance, fcc a/2<110>
            dislocations and basal hcp dislocations are typically plotted with
            ddmax=\|b\|/4.  If set to None, then no wrapping is done.
        plotxaxis : str or array-like object, optional
            Indicates the Cartesian direction associated with the system's atomic
            coordinates to align with the plotting x-axis.  Values are either 3D
            unit vectors, or strings 'x', 'y', or 'z' for the Cartesian axes
            directions.  plotxaxis and plotyaxis must be orthogonal.  Default value
            is 'x' = [1, 0, 0].
        plotyaxis : str or array-like object, optional
            Indicates the Cartesian direction associated with the system's atomic
            coordinates to align with the plotting y-axis.  Values are either 3D
            unit vectors, or strings 'x', 'y', or 'z' for the Cartesian axes
            directions.  plotxaxis and plotyaxis must be orthogonal.  Default value
            is 'y' = [0, 1, 0].
        xlim : tuple, optional
            The minimum and maximum coordinates along the plotting x-axis to
            include in the fit.  Values are taken in the specified length_unit.
            If not given, then the limits are set based on min and max atomic
            coordinates along the plotting axis.
        ylim : tuple, optional
            The minimum and maximum coordinates along the plotting y-axis to
            include in the fit.  Values are taken in the specified length_unit.
            If not given, then the limits are set based on min and max atomic
            coordinates along the plotting axis.
        zlim : tuple, optional
            The minimum and maximum coordinates normal to the plotting axes
            (i.e. plotxaxis X plotyaxis) to include in the fit.  Values are taken
            in the specified length_unit.  The optimum zlim should encompass only
            a single periodic slice.  If not given, then the limits are set
            based on min and max atomic coordinates along the axis.
        arrowscale : float, optional
            Scaling factor for the magnitude of the differential displacement
            arrows.  Default value is 1: no scaling, vectors are in units of length.
            For major components, this is often set such that the max differential
            displacement compoent after wrapping (see ddmax) is scaled to the
            distance between the atom pairs in the plot.  For minor components, this
            is often set to a large value simply to make the components visible.
        arrowwidth : float, optional
            Scaling factor to use for the width of the plotted arrows. Default value is
            0.005 = 1/200.
        use0z : bool, optional
            If False (default), the z coordinates from the reference system will be
            used for zlim and atomcmap colors. If True, the z coordinates will be
            used from system0 even if system1 is the reference system.
        atomcolor : str or list, optional
            Matplotlib color name(s) to use to display the atoms.  If str, that
            color will be assigned to all atypes.  If list, must give a color value
            or None for each atype.  Default value (None) will use cmap instead.
            Note: atomcolor and atomcmap can be used together as long as exactly
            one color or cmap is given for each unique atype.
        atomcmap : str or list, optional
            Matplotlib colormap name(s) to use to display the atoms.  Atoms will
            be colored based on their initial positions and scaled using zlim. If
            str, that cmap will be assigned to all atypes.  If list, must give a 
            cmap value or None for each atype.  Default value (None) will use 'hsv'
            cmap.  Note: atomcolor and atomcmap can be used together as long as
            exactly one color or cmap is given for each unique atype.
        atomsize : float, optional
            The circle radius size to use for the plotted atom positions in units of
            length.  Default value is 0.5.
        figsize : float or tuple, optional
            Specifies the size of the figure to create in inches.  If a single value
            is given, it will be used for the figure's width, and the height will be
            scaled based on the xlim and ylim values.  Alternatively, both the width
            and height can be set by passing a tuple of two values, but the plot will
            not be guaranteed to be "regular" with respect to length dimensions.
        matplotlib_axes : matplotlib.Axes.axes, optional
            An existing matplotlib axes object. If given, the differential displacement
            plot will be added to the specified axes of an existing figure.  This
            allows for subplots to be constructed.  Note that figsize will be ignored
            as the figure would have to be created beforehand and no automatic
            optimum scaling of the figure's dimensions will occur.
            
        Returns
        -------
        matplotlib.Figure
            The generated figure.  Not returned if matplotlib_axes is given.
        """

        ###################### Parameter and plot setup ########################

        # Interpret plot axis values
        plotxaxis = self.__plotaxisoptions(plotxaxis)
        plotyaxis = self.__plotaxisoptions(plotyaxis)

        # Build transformation matrix, T, from plot axes.
        T = axes_check([plotxaxis, plotyaxis, np.cross(plotxaxis, plotyaxis)])

        # Extract positions and transform using T        
        if self.reference == 0:        
            atompos = np.inner(self.system0.atoms.pos, T)
            refsystem = self.system0
        else:
            atompos = np.inner(self.system1.atoms.pos, T)
            refsystem = self.system1
            if use0z:
                pos0 = np.inner(self.system0.atoms.pos, T)
                atompos[:, 2] = pos0[:, 2]

        # Set default plot limits
        if xlim is None:
            xlim = (atompos[:, 0].min(), atompos[:, 0].max())
        if ylim is None:
            ylim = (atompos[:, 1].min(), atompos[:, 1].max())
        if zlim is None:
            zlim = (atompos[:, 2].min(), atompos[:, 2].max()) 

        # Define box for identifying only points inside
        plotbox = Box(xlo=xlim[0]-5, xhi=xlim[1]+5,
                      ylo=ylim[0]-5, yhi=ylim[1]+5,
                      zlo=zlim[0], zhi=zlim[1])
            
        # Set plot height if needed
        if isinstance(figsize, (int, float)):
            dx = xlim[1] - xlim[0]
            dy = ylim[1] - ylim[0]
            figsize = (figsize, figsize * dy / dx)

        # Initial plot setup and parameters
        if matplotlib_axes is None:
            fig = plt.figure(figsize=figsize, dpi=72)
            ax1 = fig.add_subplot(111)
        else:
            ax1 = matplotlib_axes
        ax1.axis([xlim[0], xlim[1], ylim[0], ylim[1]])

        # Change the scale of x and y axis
        x_major_locator=MultipleLocator(10) # every 10 steps shows the label
        y_major_locator=MultipleLocator(10)
        ax = plt.gca()
        ax.xaxis.set_major_locator(x_major_locator)
        ax.yaxis.set_major_locator(y_major_locator)

        plt.xticks(fontsize=figsize[0]*2)
        plt.yticks(fontsize=figsize[0]*2)
        
        # Handle atomcolor and atomcmap values
        atomcolor, atomcmap = self.__atomcoloroptions(atomcolor, atomcmap)

        ######################## Add atom circles to plot ##############################
        
        # Loop over all atoms i in plotting box
        for i in np.arange(refsystem.natoms)[plotbox.inside(atompos)]:
            atype = refsystem.atoms.atype[i]
            atype_index = refsystem.atypes.index(atype)

            # Plot a circle for atom i
            if atomcmap[atype_index] is not None:
                color = atomcmap[atype_index]((atompos[i, 2] - zlim[0]) / (zlim[1] - zlim[0]))
            elif atomcolor[atype_index] is not None:
                color = atomcolor[atype_index]
            else:
                color = None
            if color is not None:
                ax1.add_patch(mpatches.Circle(atompos[i, :2], atomsize, fc=color, ec='k', linewidth=figsize[0]/5))

        ######### NYE ############################
        import atomman.unitconvert as uc
        property = system.atoms.view['nye']
        property = property[tuple([Ellipsis] + nye_index)]
        assert property.shape == (system.natoms, ),  'property to plot must be a per-atom scalar'
        atompos = system.atoms.pos
        atompos = uc.get_in_units(np.inner(system.atoms.pos, T), 'angstrom')                                                                       

        in_bounds = ((atompos[:,0] > xlim[0] - 5.) &
                 (atompos[:,0] < xlim[1] + 5.) &
                 (atompos[:,1] > ylim[0] - 5.) &
                 (atompos[:,1] < ylim[1] + 5.) &
                 (atompos[:,2] > zlim[0]) &
                 (atompos[:,2] < zlim[1]))
        
        x = atompos[in_bounds, 0]
        y = atompos[in_bounds, 1]
        v = -uc.get_in_units(property[in_bounds], None)
        xy = np.vstack((x,y))
        # delete repeat value
        set = []
        for i in np.arange(xy.shape[1]):
            for j in np.arange(i+1, xy.shape[1]):
                if list(xy[:,i]) == list(xy[:,j]):
                    set.append(j)
        x = np.delete(x,set)
        y = np.delete(y,set)
        v = np.delete(v,set)

        # calculate dislocation line position, standard deviation, and moving direction
        if calculation==True:
            # ave position
            dxdy = 2.93849*4.65842*np.sqrt(3)/4 ## have to be changed when change material or orientation
            x0 = 0
            y0 = 0
            x_sq = 0
            y_sq = 0
            xy = 0
            frac = 0
            for i in np.arange(x.shape[0]):
                x0 += x[i]*v[i]*dxdy
                y0 += y[i]*v[i]*dxdy
                frac += v[i]*dxdy
            x0 = x0/frac
            y0 = y0/frac
            for i in np.arange(x.shape[0]):
                x_sq += x[i]**2*v[i]*dxdy
                y_sq += y[i]**2*v[i]*dxdy
                xy += x[i]*y[i]*v[i]*dxdy
            x_sq = x_sq/frac - x0**2
            y_sq = y_sq/frac - y0**2
            xy = xy/frac -x0*y0
            fig.x0 = x0
            fig.y0 = y0
            fig.x_sq = x_sq
            fig.y_sq = y_sq
            fig.xy = xy
            ax1.plot(x0,y0,color='blue', marker="+", markersize = 40, markeredgewidth=5, linestyle='dashed')

        from scipy.interpolate import Rbf

        range=[xlim, ylim]
        xi = np.linspace(range[0][0], range[0][1], num=xbins)
        yi = np.linspace(range[1][0], range[1][1], num=ybins)
        xi, yi = np.meshgrid(xi,yi)
        rbf = Rbf(x,y,v)
        vi = rbf(xi,yi)
        grid = vi

        # Compute intsum and avsum values
        intsum = np.sum(grid)
        avsum = intsum / (xbins-1) / (ybins-1)
        intsum = intsum * (xlim[1] - xlim[0]) / (xbins-1) * (ylim[1] - ylim[0]) / (ybins-1)
        propname=''
        czero=True

        # Get cmap from str name
        if isinstance(cmap, str):
            cmap = cm.get_cmap(cmap)

        # Set vmin = -vmax if czero is True
        if czero is True:
            vmax = abs(grid).max()
            if vmax != 0.0:
                vrounder = np.floor(np.log10(vmax))
                vmax = np.around(2 * vmax / 10.**vrounder) * 10.**vrounder / 2.
            else:
                vmax = 1e-15
            vmin = -vmax

        # Set vmin, vmax if czero is False
        else:
            vmax = grid.max()
            vmin = grid.min()

            if abs(grid).max() != 0.0:
                vrounder = np.floor(np.log10(grid.max() - grid.min()))

                vmax = np.around(2 * vmax / 10.**vrounder) * 10.**vrounder / 2.
                vmin = np.around(2 * vmin / 10.**vrounder) * 10.**vrounder / 2.

                if vmax == vmin:
                    if vmax > 0:
                        vmin = 0
                    else:
                        vmax = 0

            else:
                vmax = 1e-15
                vmin = -1e-15

        # Scale values if needed
        vmin *= scale
        vmax *= scale
        #vmin = -0.055
        #vmax = 0.055
        # Generate plot
        lims = dict(cmap = cmap, norm=plt.Normalize(vmax=vmax, vmin=vmin))
        plt.pcolormesh(xi,yi,vi,shading='flat',**lims)

        # Add pretty colorbar
        vticks = np.linspace(vmax, vmin, 3, endpoint=True)                          
        cbar = plt.colorbar(fraction=0.04, pad = 0.04, ticks=vticks)
        cbar.ax.tick_params(labelsize=figsize[0]*2)

        # Make axis values and title pretty


        ######################## Arrow setup ##############################
        
        # Build arrows based on component
        arrowlengths, arrowcenters = self.__buildarrows(T, plotbox, component, ddmax, alat)
        
        # Scale arrows
        arrowlengths = arrowscale * arrowlengths
        
        # Compute arrow widths based on lengths
        arrowwidths = arrowwidth * (arrowlengths[:,0]**2 + arrowlengths[:,1]**2)**0.5

        # Plot the arrows
        for center, length, width in zip(arrowcenters, arrowlengths, arrowwidths):
            if width > 1e-7:
                ax1.quiver(center[0], center[1], length[0], length[1],
                           pivot='middle', angles='xy', scale_units='xy',
                           scale=1, width=width, minshaft=2)

        #ax1.plot(2.93749682368896/2,0,color='blue',marker="+",linestyle='dashed',
               # linewidth=4, markersize=60.0)

        ax1.set_aspect('equal')
        if matplotlib_axes is None:
            return fig
    
    def __plotaxisoptions(self, plotaxis):
        """Internal method for handling plotxaxis and plotyaxis values"""
        
        # Give numeric values for str plot axis terms
        if plotaxis == 'x':
            plotaxis = [1.0, 0.0, 0.0]
        elif plotaxis == 'y':
            plotaxis = [0.0, 1.0, 0.0]
        elif plotaxis == 'z':
            plotaxis = [0.0, 0.0, 1.0]
        
        # Convert to numpy array
        return np.asarray(plotaxis, dtype=float)
    
    def __atomcoloroptions(self, atomcolor, atomcmap):
        """Internal method for handling atomcolor and atomcmap options"""
        
        # Identify number of atom types in the reference system
        if self.reference == 0:
            natypes = self.system0.natypes
        else:
            natypes = self.system1.natypes
        
        # Set default atomcmap
        if atomcolor is None and atomcmap is None:
            atomcmap = 'hsv'

        # Transform single color/cmap values to lists
        if isinstance(atomcmap, str):
            if atomcolor is not None:
                raise TypeError('atomcmap and atomcolor cannot be str if both are given')
            atomcmap = [atomcmap for i in range(natypes)]
            atomcolor = [None for i in range(natypes)]
        elif isinstance(atomcolor, str):
            if atomcmap is not None:
                raise TypeError('atomcmap and atomcolor cannot be str if both are given')
            atomcolor = [atomcolor for i in range(natypes)]
            atomcmap = [None for i in range(natypes)]
        else:
            atomcolor = list(atomcolor)
            atomcmap = list(atomcmap)

        # Check atomcolor, atomcmap list compatibility
        if len(atomcmap) != natypes:
            raise ValueError('Invalid number of atomcmap values')
        if len(atomcolor) != natypes:
            raise ValueError('Invalid number of atomcolor values')
        for ic in range(len(atomcmap)):
            if atomcmap[ic] is not None:
                if atomcolor[ic] is not None:
                    raise ValueError('atomcmap and atomcolor cannot both be given for same atype')
                atomcmap[ic] = cm.get_cmap(atomcmap[ic])
        
        return atomcolor, atomcmap
    
    def __buildarrows(self, T, plotbox, component, ddmax, alat):
        """Internal method for building the parameters for plotting the arrows"""
        
        # Manage component
        if isinstance(component, str):
            if component == 'x':
                component = np.array([1.0, 0.0, 0.0])
            elif component == 'y':
                component = np.array([0.0, 1.0, 0.0])
            elif component == 'z':
                component = np.array([0.0, 0.0, 1.0])
            elif component != 'projection':
                raise ValueError('Invalid component style: must be x, y, z, projection, or numpy array')
        else:
            component = np.asarray(component, dtype=float)
            assert component.shape == (3,), 'Invalid numeric component: must be a 3D vector'
            component = component / np.linalg.norm(component)
            
        # Transform arrow-related vectors
        ddvectors = np.inner(self.ddvectors, T)
        arrowcenters = np.inner(self.arrowcenters, T)
        arrowuvectors = np.inner(self.arrowuvectors, T)
                
        # Identify only vectors in ploting box
        inbounds = plotbox.inside(arrowcenters)
        ddvectors = ddvectors[inbounds]
        arrowcenters = arrowcenters[inbounds]
        arrowuvectors = arrowuvectors[inbounds]

        # Build arrows for the xy component option
        if isinstance(component, str) and component == 'projection':
            
            # Arrows are in-plane vector components
            ddcomponents = (ddvectors[:,0]**2 + ddvectors[:,1]**2)**0.5
            ddcomponents[ddcomponents<0.1*alat] = 0
            arrowuvectors = ddvectors[:, :2] / ddcomponents[:,np.newaxis]
            
            # Scheme for direction uniqueness (not sure what other projects use?)
            arrowuvectors[ddvectors[:, 2] > 0] *= -1
            
            # Normalize ddcomponents to be between +-ddmax
            if ddmax is not None and ddmax > 0:
                while True:
                    mask = ddcomponents > ddmax
                    if np.sum(mask) == 0:
                        break
                    ddcomponents[mask] -= 2 * ddmax
                while True:
                    mask = ddcomponents < -ddmax
                    if np.sum(mask) == 0:
                        break
                    ddcomponents[mask] += 2 * ddmax

            # Arrows have magnitude of ddcomponent
            arrowlengths = arrowuvectors * ddcomponents[:,np.newaxis]
        
        # Build arrows for vector components
        else:
            component = T.dot(component)
            ddcomponents = ddvectors.dot(component)
            ddcomponents[ddcomponents<0.1*alat] = 0

            # Normalize ddcomponents to be between +-ddmax
            if ddmax is not None and ddmax > 0:
                while True:
                    mask = ddcomponents > ddmax
                    if np.sum(mask) == 0:
                        break
                    ddcomponents[mask] -= 2 * ddmax
                while True:
                    mask = ddcomponents < -ddmax
                    if np.sum(mask) == 0:
                        break
                    ddcomponents[mask] += 2 * ddmax

            # Arrows have magnitude of ddcomponent and direction of uvectors
            arrowlengths = arrowuvectors * ddcomponents[:,np.newaxis]
        
        return arrowlengths, arrowcenters

    def ddplot(self, component, ddmax, plotxaxis='x', plotyaxis='y',
             xlim=None, ylim=None, zlim=None,
             arrowscale=1, arrowwidth=0.005,  use0z=False,
             atomcolor=None, atomcmap=None, atomsize=0.5, figsize=10,
             matplotlib_axes=None):

        r"""
        Creates a matplotlib figure of a differential displacement map.  Atom
        positions are represented as circles, while the selected components of the
        differential displacement vectors are plotted as arrows.

        Parameters
        ----------
        component : str or array-like object
            Indicates the component(s) of the differential displacement to plot.
            Values of 'x', 'y', or 'z' will plot the component along that
            Cartesian direction.  A value of 'projection' will plot the
            differential displacement vectors as projected onto the plotting
            plane, thereby showing the two components perpendicular to the line
            direction.  If a 3D vector is given, then the component parallel to
            that direction will be used.
        ddmax : float or None
            The maximum differential displacement value allowed. Values will be
            kept between +-ddmax by wrapping values with larger absolute values
            around by adding/subtracting 2*ddmax. Typically, this is set to be
            \|b\|/2, but can be defect-specific. For instance, fcc a/2<110>
            dislocations and basal hcp dislocations are typically plotted with
            ddmax=\|b\|/4.  If set to None, then no wrapping is done.
        plotxaxis : str or array-like object, optional
            Indicates the Cartesian direction associated with the system's atomic
            coordinates to align with the plotting x-axis.  Values are either 3D
            unit vectors, or strings 'x', 'y', or 'z' for the Cartesian axes
            directions.  plotxaxis and plotyaxis must be orthogonal.  Default value
            is 'x' = [1, 0, 0].
        plotyaxis : str or array-like object, optional
            Indicates the Cartesian direction associated with the system's atomic
            coordinates to align with the plotting y-axis.  Values are either 3D
            unit vectors, or strings 'x', 'y', or 'z' for the Cartesian axes
            directions.  plotxaxis and plotyaxis must be orthogonal.  Default value
            is 'y' = [0, 1, 0].
        xlim : tuple, optional
            The minimum and maximum coordinates along the plotting x-axis to
            include in the fit.  Values are taken in the specified length_unit.
            If not given, then the limits are set based on min and max atomic
            coordinates along the plotting axis.
        ylim : tuple, optional
            The minimum and maximum coordinates along the plotting y-axis to
            include in the fit.  Values are taken in the specified length_unit.
            If not given, then the limits are set based on min and max atomic
            coordinates along the plotting axis.
        zlim : tuple, optional
            The minimum and maximum coordinates normal to the plotting axes
            (i.e. plotxaxis X plotyaxis) to include in the fit.  Values are taken
            in the specified length_unit.  The optimum zlim should encompass only
            a single periodic slice.  If not given, then the limits are set
            based on min and max atomic coordinates along the axis.
        arrowscale : float, optional
            Scaling factor for the magnitude of the differential displacement
            arrows.  Default value is 1: no scaling, vectors are in units of length.
            For major components, this is often set such that the max differential
            displacement compoent after wrapping (see ddmax) is scaled to the
            distance between the atom pairs in the plot.  For minor components, this
            is often set to a large value simply to make the components visible.
        arrowwidth : float, optional
            Scaling factor to use for the width of the plotted arrows. Default value is
            0.005 = 1/200.
        use0z : bool, optional
            If False (default), the z coordinates from the reference system will be
            used for zlim and atomcmap colors. If True, the z coordinates will be
            used from system0 even if system1 is the reference system.
        atomcolor : str or list, optional
            Matplotlib color name(s) to use to display the atoms.  If str, that
            color will be assigned to all atypes.  If list, must give a color value
            or None for each atype.  Default value (None) will use cmap instead.
            Note: atomcolor and atomcmap can be used together as long as exactly
            one color or cmap is given for each unique atype.
        atomcmap : str or list, optional
            Matplotlib colormap name(s) to use to display the atoms.  Atoms will
            be colored based on their initial positions and scaled using zlim. If
            str, that cmap will be assigned to all atypes.  If list, must give a
            cmap value or None for each atype.  Default value (None) will use 'hsv'
            cmap.  Note: atomcolor and atomcmap can be used together as long as
            exactly one color or cmap is given for each unique atype.
        atomsize : float, optional
            The circle radius size to use for the plotted atom positions in units of
            length.  Default value is 0.5.
        figsize : float or tuple, optional
            Specifies the size of the figure to create in inches.  If a single value
            is given, it will be used for the figure's width, and the height will be
            scaled based on the xlim and ylim values.  Alternatively, both the width
            and height can be set by passing a tuple of two values, but the plot will
            not be guaranteed to be "regular" with respect to length dimensions.
        matplotlib_axes : matplotlib.Axes.axes, optional
            An existing matplotlib axes object. If given, the differential displacement
            plot will be added to the specified axes of an existing figure.  This
            allows for subplots to be constructed.  Note that figsize will be ignored
            as the figure would have to be created beforehand and no automatic
            optimum scaling of the figure's dimensions will occur.

        Returns
        -------
        matplotlib.Figure
            The generated figure.  Not returned if matplotlib_axes is given.
        """

        ###################### Parameter and plot setup ########################

        # Interpret plot axis values
        plotxaxis = self.__plotaxisoptions(plotxaxis)
        plotyaxis = self.__plotaxisoptions(plotyaxis)

        # Build transformation matrix, T, from plot axes.
        T = axes_check([plotxaxis, plotyaxis, np.cross(plotxaxis, plotyaxis)])

        # Extract positions and transform using T
        if self.reference == 0:
            atompos = np.inner(self.system0.atoms.pos, T)
            refsystem = self.system0
        else:
            atompos = np.inner(self.system1.atoms.pos, T)
            refsystem = self.system1
            if use0z:
                pos0 = np.inner(self.system0.atoms.pos, T)
                atompos[:, 2] = pos0[:, 2]

        # Set default plot limits
        if xlim is None:
            xlim = (atompos[:, 0].min(), atompos[:, 0].max())
        if ylim is None:
            ylim = (atompos[:, 1].min(), atompos[:, 1].max())
        if zlim is None:
            zlim = (atompos[:, 2].min(), atompos[:, 2].max())

        # Define box for identifying only points inside
        plotbox = Box(xlo=xlim[0]-5, xhi=xlim[1]+5,
                      ylo=ylim[0]-5, yhi=ylim[1]+5,
                      zlo=zlim[0], zhi=zlim[1])

        # Set plot height if needed
        if isinstance(figsize, (int, float)):
            dx = xlim[1] - xlim[0]
            dy = ylim[1] - ylim[0]
            figsize = (figsize, figsize * dy / dx)

        # Initial plot setup and parameters
        if matplotlib_axes is None:
            fig = plt.figure(figsize=figsize, dpi=72)
            ax1 = fig.add_subplot(111)
        else:
            ax1 = matplotlib_axes
        ax1.axis([xlim[0], xlim[1], ylim[0], ylim[1]])
        plt.xticks(fontsize=figsize[0]*1.5)
        plt.yticks(fontsize=figsize[0]*1.5)
        # Handle atomcolor and atomcmap values
        atomcolor, atomcmap = self.__atomcoloroptions(atomcolor, atomcmap)

        ######################## Add atom circles to plot ##############################

        # Loop over all atoms i in plotting box
        for i in np.arange(refsystem.natoms)[plotbox.inside(atompos)]:
            atype = refsystem.atoms.atype[i]
            atype_index = refsystem.atypes.index(atype)

            # Plot a circle for atom i
            if atomcmap[atype_index] is not None:
                color = atomcmap[atype_index]((atompos[i, 2] - zlim[0]) / (zlim[1] - zlim[0]))
            elif atomcolor[atype_index] is not None:
                color = atomcolor[atype_index]
            else:
                color = None
            if color is not None:
                ax1.add_patch(mpatches.Circle(atompos[i, :2], atomsize, fc=color, ec='k',linewidth=figsize[0]/5))

        ######################## Arrow setup ##############################

        # Build arrows based on component
        arrowlengths, arrowcenters = self.__buildarrows(T, plotbox, component, ddmax, 0)

        # Scale arrows
        arrowlengths = arrowscale * arrowlengths

        # Compute arrow widths based on lengths
        arrowwidths = arrowwidth * (arrowlengths[:,0]**2 + arrowlengths[:,1]**2)**0.5

        # Plot the arrows
        for center, length, width in zip(arrowcenters, arrowlengths, arrowwidths):
            if width > 1e-7:
                ax1.quiver(center[0], center[1], length[0], length[1],
                           pivot='middle', angles='xy', scale_units='xy',
                           scale=1, width=width, minshaft=2)
        #ax1.plot(0,0,"r+",markersize=25.0)
        #ax1.plot(np.sqrt(6)/12*4.05,np.sqrt(3)/6*4.05,"r+",markersize=25.0)
        if matplotlib_axes is None:
            return fig
