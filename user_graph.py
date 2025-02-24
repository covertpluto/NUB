from math import pi, sqrt, asin, sin, cos, atan, radians, atan2
from apis import AddressToCoords

addr_service = AddressToCoords(service="nominatim")

EARTH_RADIUS = 6356  # km


class GeolocationError(Exception):
    pass


class UserNode:
    def __init__(self, coords, email):
        # Coordinates in [lat, long]
        self.__coords = coords
        self.__email = email

        # Dictionary of other nodes
        self.__neighbours = {}

    def get_coords(self):
        return self.__coords

    def get_email(self):
        return self.__email

    def set_neighbours(self, neighbours):
        self.__neighbours = neighbours

    def get_neighbours(self):
        return self.__neighbours


class Graph:
    def __init__(self):
        self.__nodes = []

    def check_node(self, node_email):
        for node in self.__nodes:
            if node.get_email() == node_email:
                return True
        return False

    def merge_sort_neighbours(self, distances):
        if len(distances) <= 1:
            return distances
        print(distances)

        # split the list in half
        midp = len(distances) // 2
        left_half = distances[:midp]
        right_half = distances[midp:]

        left_sorted = self.merge_sort_neighbours(left_half)
        right_sorted = self.merge_sort_neighbours(right_half)

        return self.merge_neighbours(left_sorted, right_sorted)

    def merge_neighbours(self, left_sorted, right_sorted):
        sorted = []
        idx_left = 0
        idx_right = 0

        # merge both sides
        while idx_left < len(left_sorted) and idx_right < len(right_sorted):
            if left_sorted[idx_left][0] < right_sorted[idx_right][0]:
                sorted.append(left_sorted[idx_left])
                idx_left += 1
            else:
                sorted.append(right_sorted[idx_right])
                idx_right += 1

        for l in left_sorted[idx_left:]:
            sorted.append(l)
        for r in right_sorted[idx_right:]:
            sorted.append(r)

        return sorted

    def sort_nodes(self, nodes):
        node_list = list(zip(nodes.values(), nodes.keys()))
        nodes_sorted = self.merge_sort_neighbours(node_list)
        result = {}
        for node in nodes_sorted:
            result[node[1]] = node[0]
        return result

    def nearby_nodes(self, email, distance=20):
        this_node = [node for node in self.__nodes if node.get_email() == email][0]
        this_node_neighbours_sorted = self.sort_nodes(this_node.get_neighbours())

        print(this_node_neighbours_sorted)
        return this_node_neighbours_sorted

    def new_node(self, addr_lines, email):
        try:
            # convert the text address into coordinates to create a new node
            coords, display_name = addr_service.convert_address(addr_lines)
            node = UserNode(coords, email)
            self.__nodes.append(node)
            return 0
        except IndexError:
            # sometimes the API might fail (overload, loss of connection, rate limit)
            print("Resolve geolocation failed, API fail?")

            # Raise GeolocationError
            raise GeolocationError

    def calculate_distance(self, coordA, coordB):

        # # convert lat and long from degrees to radians
        # lat1, lon1 = radians(coordA[0]), radians(coordA[1])
        # lat2, lon2 = radians(coordB[0]), radians(coordB[1])
        #
        # dlat = sin((lat2 - lat1) / 2)
        # dlon = sin((lon2 - lon1) / 2)
        #
        # a = sin(dlat) ** 2 + cos(lat1) * cos(lat2) * sin(dlon) ** 2
        # c = 2 * atan2(sqrt(a), sqrt(1 - a))
        # dist = EARTH_RADIUS * c

        # get the differences in longitude and latitude, then convert to radians
        lat_delta = abs(coordA[0] - coordB[0]) * (pi / 180)
        long_delta = abs(coordA[1] - coordB[1]) * (pi / 180)

        # arc length = angle X radius

        lat_arc_length = EARTH_RADIUS * lat_delta
        long_arc_length = EARTH_RADIUS * long_delta

        # apply pythagoras on two arc lengths
        dist = sqrt(lat_arc_length ** 2 + long_arc_length ** 2)  # in km

        return round(dist, 1)

    def build_adjacency_list(self, this_node, other_nodes):
        # print(f"Building adjacency list for {this_node.get_email()}")

        # start with this node's location
        this_coords = this_node.get_coords()
        adjacency = {}

        # we want to calculate distances from other nodes
        for other_node in other_nodes:
            other_node_coords = other_node.get_coords()

            # calculate distance function defined above
            dist = self.calculate_distance(this_coords, other_node_coords)

            # if too far, there's no good reason to connect.
            if dist < 300:
                # add it to the dictionary (email: distance)
                adjacency[other_node.get_email()] = dist

        # put this back in the node currently being operated on
        this_node.set_neighbours(adjacency)

    def build_adjacency_lists(self):
        # does the above for every node
        for node in self.__nodes:
            other_nodes = [node for node in self.__nodes]
            other_nodes.remove(node)
            self.build_adjacency_list(node, other_nodes)
            self.print_all_nodes_neighbours()

    def print_all_nodes_neighbours(self):
        for node in self.__nodes:
            print(node.get_email(), ":", node.get_neighbours())

#
#
# graph = Graph()
#
#
# graph.new_node(["196 Duke's Ride", "Crowthorne", "RG45 6DS", "United Kingdom"], "test1")
# graph.new_node(["51 New Road", "Harlington", "UB3 5BQ", "United Kingdom"], "test5")
#
# graph.new_node(["90 End Lane", "Harlington", "UB3 5LU", "United Kingdom"], "test3")
# graph.new_node(["246 Wincolmlee", "Hull", "HU2 0PZ", "United Kingdom"], "test4")
# graph.new_node(["945 Barbara Ave", "Mountain View", "CA 94040", "United States"], "test2")
# graph.build_adjacency_lists()
#
# print("\n\nAll nodes and neighbours")
# graph.print_all_nodes_neighbours()
#
# print()
# graph.nearby_nodes("test3")
#
